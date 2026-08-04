from django.http import HttpResponseForbidden
from functools import wraps
from django.shortcuts import render, redirect
from django.http import HttpResponse
def check_permission(function_name):
    """
    Decorator to check if the user has permission for the given function.
    Function name should be passed as an argument to this decorator.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            permissions = request.session.get('permissions', {})
            request.session['current_page'] = function_name

            if not permissions.get(function_name):
                return custom_forbidden(request)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# def check_permission(function_name):
#     """
#     Decorator to check if the user has permission for the given function.
#     Function name should be passed as an argument to this decorator.
#     """
#     def decorator(view_func):
#         @wraps(view_func)
#         def _wrapped_view(request, *args, **kwargs):
#             # Retrieve permissions from the session
#             permissions = request.session.get('permissions', {})
#             request.session['current_page']=function_name
#             # Check if the user has permission for the specific function
#             if permissions.get(function_name, False) is False:
#                 # User doesn't have permission, return 403 Forbidden
#                 return custom_forbidden(request)

#             # Proceed with the view logic if permission is granted
#             return view_func(request, *args, **kwargs)
        
#         return _wrapped_view
#     return decorator

from django.http import HttpResponse

def no_cache(view_func):
    def _wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)

        # Ensure response is an instance of HttpResponse before proceeding
        if not isinstance(response, HttpResponse):
            return HttpResponse("Internal Server Error", status=500)

        # Set the Cache-Control headers to prevent caching
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        return response
    return _wrapped_view

def is_super_user(function_name):
    
    def superuser_required(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            request.session['current_page']=function_name
            if not request.user.is_superuser:
                return redirect('logout')
            return function(request, *args, **kwargs)
        return wrapper
    return superuser_required

def custom_forbidden(request):
    html_content = """
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f7f7f7;
                text-align: center;
                padding: 50px;
            }
            .container {
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                padding: 40px;
                width: 80%;
                max-width: 600px;
                margin: 0 auto;
            }
            h1 {
                color: #d9534f;
                font-size: 36px;
                margin-bottom: 20px;
            }
            p {
                color: #666;
                font-size: 18px;
                margin-bottom: 30px;
            }
            .button {
                background-color: #5bc0de;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                font-size: 16px;
                border-radius: 5px;
                transition: background-color 0.3s;
            }
            .button:hover {
                background-color: #31b0d5;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Forbidden Access</h1>
            <p>You do not have permission to access this page.</p>
            <a href="/main/" class="button">Go Back to Home</a>
        </div>
    </body>
    </html>
    """
    return HttpResponseForbidden(html_content)






def faculty_login_required(view_func):
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # # print("request.session.get('employee_id') => ", request.session.get("employee_id"))
        if not request.session.get("employee_id"):
            return redirect('login_view')
        return view_func(request, *args, **kwargs)
    return wrapper

