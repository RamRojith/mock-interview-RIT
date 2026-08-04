from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from user_accounts.audit import (
    append_audit_log,
    diff_snapshots,
    get_actor_payload,
    get_current_request,
    get_request_details,
    model_snapshot,
    should_track_model,
)


def _build_log_payload(request, user):
    payload = get_actor_payload(user)
    payload.update(get_request_details(request))
    return payload


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    append_audit_log(
        event_type="login",
        description="User logged in successfully.",
        **_build_log_payload(request, user),
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if not request or not user:
        return

    append_audit_log(
        event_type="logout",
        description="User logged out.",
        **_build_log_payload(request, user),
    )


@receiver(pre_save)
def capture_previous_model_state(sender, instance, using, **kwargs):
    if not should_track_model(sender):
        return

    request = get_current_request()
    user = getattr(request, "user", None) if request else None
    if not user or not getattr(user, "is_authenticated", False):
        return

    if not getattr(instance, "pk", None):
        instance._audit_old_snapshot = {}
        return

    existing = sender._default_manager.using(using).filter(pk=instance.pk).first()
    instance._audit_old_snapshot = model_snapshot(existing) if existing else {}


@receiver(post_save)
def log_model_save(sender, instance, created, using, **kwargs):
    if not should_track_model(sender):
        return

    request = get_current_request()
    user = getattr(request, "user", None) if request else None
    if not request or not user or not getattr(user, "is_authenticated", False):
        return

    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    old_snapshot = getattr(instance, "_audit_old_snapshot", {}) or {}
    new_snapshot = model_snapshot(instance)

    if created:
        event_type = "data_create"
        changed_fields = {key: {"from": None, "to": value} for key, value in new_snapshot.items()}
        description = f"Created {sender._meta.verbose_name.title()}."
    else:
        changed_fields = diff_snapshots(old_snapshot, new_snapshot)
        if not changed_fields:
            return

        if sender._meta.app_label == "user_accounts" and sender.__name__ == "USER":
            only_last_login = set(changed_fields.keys()) == {"last_login"}
            if only_last_login:
                return

        event_type = "data_update"
        description = f"Updated {sender._meta.verbose_name.title()}."

    payload = _build_log_payload(request, user)
    payload.update(
        app_label=sender._meta.app_label,
        model_name=sender._meta.model_name,
        object_pk=str(getattr(instance, "pk", "")),
        object_repr=str(instance),
        description=description,
        changed_fields=changed_fields,
    )

    append_audit_log(event_type=event_type, **payload)


@receiver(post_delete)
def log_model_delete(sender, instance, using, **kwargs):
    if not should_track_model(sender):
        return

    request = get_current_request()
    user = getattr(request, "user", None) if request else None
    if not request or not user or not getattr(user, "is_authenticated", False):
        return

    if request.method not in {"POST", "DELETE"}:
        return

    payload = _build_log_payload(request, user)
    payload.update(
        app_label=sender._meta.app_label,
        model_name=sender._meta.model_name,
        object_pk=str(getattr(instance, "pk", "")),
        object_repr=str(instance),
        description=f"Deleted {sender._meta.verbose_name.title()}.",
        changed_fields={key: {"from": value, "to": None} for key, value in model_snapshot(instance).items()},
    )

    append_audit_log(event_type="data_delete", **payload)
