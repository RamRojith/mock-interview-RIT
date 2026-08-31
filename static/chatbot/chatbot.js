(() => {
  "use strict";

  const root = document.getElementById("facultyChatbot");
  if (!root) return;

  const panel = document.getElementById("facultyChatPanel");
  const toggle = document.getElementById("facultyChatToggle");
  const close = document.getElementById("facultyChatClose");
  const clear = document.getElementById("facultyChatClear");
  const form = document.getElementById("facultyChatForm");
  const input = document.getElementById("facultyChatInput");
  const send = document.getElementById("facultyChatSend");
  const messages = document.getElementById("facultyChatMessages");
  const empty = document.getElementById("facultyChatEmpty");
  const status = document.getElementById("facultyChatStatus");
  const questionToggle = document.getElementById("erpChatQuestionsToggle");
  const questionPanel = document.getElementById("erpChatQuestions");
  const questionClose = document.getElementById("erpChatQuestionsClose");
  const questionSearch = document.getElementById("erpChatQuestionsSearch");
  const questionList = document.getElementById("erpChatQuestionsList");
  const questionEmpty = document.getElementById("erpChatQuestionsEmpty");
  const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]").value;
  let historyLoaded = false;
  let busy = false;

  let questionGroups = [];
  let questionsLoaded = false;
  let questionsLoading = null;

  function resizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 116)}px`;
  }

  async function loadQuestionGroups() {
    if (questionsLoaded) return;
    if (questionsLoading) return questionsLoading;

    questionList.setAttribute("aria-busy", "true");
    questionList.replaceChildren();
    questionEmpty.textContent = "Loading permitted questions...";
    questionEmpty.hidden = false;

    questionsLoading = fetch(root.dataset.questionsUrl, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error(data.error || "Unable to load permitted questions.");
        }
        questionGroups = (Array.isArray(data.groups) ? data.groups : [])
          .filter((group) => group && typeof group.title === "string" && Array.isArray(group.questions))
          .map((group) => ({
            title: group.title,
            questions: group.questions.filter((question) => typeof question === "string"),
          }));
        questionsLoaded = true;
        questionEmpty.textContent = "No matching questions found.";
        renderQuestions();
      })
      .catch((error) => {
        questionGroups = [];
        questionEmpty.textContent = error.message || "Unable to load permitted questions.";
        questionEmpty.hidden = false;
      })
      .finally(() => {
        questionList.removeAttribute("aria-busy");
        questionsLoading = null;
      });

    return questionsLoading;
  }

  function setQuestionsOpen(open) {
    if (!questionPanel || !questionToggle) return;
    questionPanel.hidden = !open;
    questionToggle.setAttribute("aria-expanded", String(open));
    if (open) {
      loadQuestionGroups();
      if (questionSearch) questionSearch.focus();
    } else if (questionSearch) {
      questionSearch.value = "";
      renderQuestions();
    }
  }

  function useQuestion(question) {
    input.value = question;
    resizeInput();
    setQuestionsOpen(false);
    input.focus();
    input.setSelectionRange(question.length, question.length);
    status.textContent = "Question added. Edit any semester or subject details, then send.";
  }

  async function copyQuestion(question, button) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(question);
      } else {
        const copyArea = document.createElement("textarea");
        copyArea.value = question;
        copyArea.setAttribute("readonly", "");
        copyArea.style.position = "fixed";
        copyArea.style.opacity = "0";
        document.body.appendChild(copyArea);
        copyArea.select();
        const copied = document.execCommand("copy");
        copyArea.remove();
        if (!copied) throw new Error("Copy was not available.");
      }
      button.innerHTML = '<i class="fas fa-check" aria-hidden="true"></i>';
      button.setAttribute("aria-label", `Copied: ${question}`);
      status.textContent = "Question copied.";
      window.setTimeout(() => {
        button.innerHTML = '<i class="fas fa-copy" aria-hidden="true"></i>';
        button.setAttribute("aria-label", `Copy: ${question}`);
      }, 1200);
    } catch (error) {
      status.textContent = "Unable to copy automatically. Select the question to place it in the message box.";
    }
  }

  function renderQuestions() {
    if (!questionList || !questionEmpty) return;
    const searchTerm = (questionSearch?.value || "").trim().toLowerCase();
    questionList.replaceChildren();
    let visibleCount = 0;

    questionGroups.forEach((group) => {
      const questions = group.questions.filter((question) =>
        `${group.title} ${question}`.toLowerCase().includes(searchTerm)
      );
      if (!questions.length) return;

      const section = document.createElement("section");
      section.className = "faculty-chatbot__question-group";
      const heading = document.createElement("h4");
      heading.textContent = group.title;
      section.appendChild(heading);

      questions.forEach((question) => {
        visibleCount += 1;
        const row = document.createElement("div");
        row.className = "faculty-chatbot__question-row";

        const selectButton = document.createElement("button");
        selectButton.type = "button";
        selectButton.className = "faculty-chatbot__question-select";
        selectButton.textContent = question;
        selectButton.addEventListener("click", () => useQuestion(question));

        const copyButton = document.createElement("button");
        copyButton.type = "button";
        copyButton.className = "faculty-chatbot__question-copy";
        copyButton.setAttribute("aria-label", `Copy: ${question}`);
        copyButton.title = "Copy question";
        copyButton.innerHTML = '<i class="fas fa-copy" aria-hidden="true"></i>';
        copyButton.addEventListener("click", () => copyQuestion(question, copyButton));

        row.append(selectButton, copyButton);
        section.appendChild(row);
      });
      questionList.appendChild(section);
    });

    questionEmpty.hidden = visibleCount > 0;
  }

  function setOpen(open) {
    if (!open) setQuestionsOpen(false);
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.hidden = open;
    if (open) {
      loadHistory();
      window.setTimeout(() => input.focus(), 40);
    }
  }

  function appendReportContent(bubble, content) {
    const lines = String(content ?? "").split(/\r?\n/);
    let textLines = [];

    const appendInlineFormatting = (element, value) => {
      const pattern = /\*\*([^*\n]+)\*\*/g;
      let cursor = 0;
      let match;
      while ((match = pattern.exec(value)) !== null) {
        if (match.index > cursor) {
          element.appendChild(document.createTextNode(value.slice(cursor, match.index)));
        }
        const strong = document.createElement("strong");
        strong.textContent = match[1];
        element.appendChild(strong);
        cursor = pattern.lastIndex;
      }
      if (cursor < value.length) {
        element.appendChild(document.createTextNode(value.slice(cursor)));
      }
    };

    const flushText = () => {
      if (!textLines.length) return;
      const text = document.createElement("div");
      text.className = "faculty-chatbot__text";
      textLines.forEach((line, index) => {
        appendInlineFormatting(text, line);
        if (index < textLines.length - 1) {
          text.appendChild(document.createTextNode("\n"));
        }
      });
      bubble.appendChild(text);
      textLines = [];
    };

    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];

      const isDashSeparator = /^\s*[-]{4,}\s*$/.test(line);
      const isPipeSeparator = /^\s*[:\-+| ]+\s*$/.test(line) && line.includes("|");

      const useDashFormat = isDashSeparator && index > 0 && index + 1 < lines.length;
      const usePipeFormat = isPipeSeparator && index > 0 && index + 1 < lines.length;

      if (useDashFormat) {
        const prevLine = lines[index - 1].trim();
        const nextLine = lines[index + 1].trim();
        const prevParts = prevLine.split(/\s{2,}/).filter(Boolean);
        const nextParts = nextLine.split(/\s{2,}/).filter(Boolean);
        if (prevParts.length >= 2 && nextParts.length >= 2 && prevParts.length === nextParts.length) {
          flushText();
          const colCount = prevParts.length;
          const headerCells = prevParts;
          const rows = [];
          let dataLine = nextLine;
          while (true) {
            const parts = dataLine.trim().split(/\s{2,}/).filter(Boolean);
            if (parts.length !== colCount) break;
            rows.push(parts);
            index += 1;
            if (index + 1 >= lines.length) break;
            const peek = lines[index + 1].trim();
            if (!peek || /^\s*[-]{4,}\s*$/.test(peek)) break;
            dataLine = peek;
          }

          const tableWrap = document.createElement("div");
          tableWrap.className = "faculty-chatbot__table-wrap";
          tableWrap.setAttribute("tabindex", "0");
          tableWrap.setAttribute("role", "region");
          tableWrap.setAttribute("aria-label", "Marks table");

          const table = document.createElement("table");
          table.className = "faculty-chatbot__table";
          const head = document.createElement("thead");
          const headRow = document.createElement("tr");
          headerCells.forEach((label) => {
            const cell = document.createElement("th");
            cell.scope = "col";
            cell.textContent = label;
            headRow.appendChild(cell);
          });
          head.appendChild(headRow);
          table.appendChild(head);

          const body = document.createElement("tbody");
          rows.forEach((values) => {
            const row = document.createElement("tr");
            values.forEach((value) => {
              const cell = document.createElement("td");
              cell.textContent = value;
              row.appendChild(cell);
            });
            body.appendChild(row);
          });
          table.appendChild(body);
          tableWrap.appendChild(table);
          bubble.appendChild(tableWrap);
          continue;
        }
      }

      if (usePipeFormat) {
        const headerLine = lines[index - 1].trim();
        const displayHeaders = headerLine.split("|").map((cell) => cell.trim()).filter(Boolean);
        if (displayHeaders.length >= 2) {
          textLines.pop();
          flushText();
          const colCount = displayHeaders.length;
          const rows = [];
          while (index + 1 < lines.length) {
            const nextLine = lines[index + 1];
            const isSep = /^\s*[:\-+| ]+\s*$/.test(nextLine) && nextLine.includes("|");
            const rowCells = nextLine.split("|").map((cell) => cell.trim());
            const isDataRow = rowCells.length === colCount;
            if (!isSep && !isDataRow) break;
            index += 1;
            if (isDataRow) rows.push(rowCells);
          }

          const tableWrap = document.createElement("div");
          tableWrap.className = "faculty-chatbot__table-wrap";
          tableWrap.setAttribute("tabindex", "0");
          tableWrap.setAttribute("role", "region");
          tableWrap.setAttribute("aria-label", "Data table");

          const table = document.createElement("table");
          table.className = "faculty-chatbot__table";
          const head = document.createElement("thead");
          const headRow = document.createElement("tr");
          displayHeaders.forEach((label) => {
            const cell = document.createElement("th");
            cell.scope = "col";
            cell.textContent = label;
            headRow.appendChild(cell);
          });
          head.appendChild(headRow);
          table.appendChild(head);

          const body = document.createElement("tbody");
          rows.forEach((values) => {
            const row = document.createElement("tr");
            values.forEach((value) => {
              const cell = document.createElement("td");
              cell.textContent = value;
              row.appendChild(cell);
            });
            body.appendChild(row);
          });
          table.appendChild(body);
          tableWrap.appendChild(table);
          bubble.appendChild(tableWrap);
          continue;
        }
      }

      textLines.push(line);
    }

    flushText();
  }

  function addMessage(role, content) {
    empty.hidden = true;
    const row = document.createElement("div");
    row.className = `faculty-chatbot__message faculty-chatbot__message--${role}`;
    const bubble = document.createElement("div");
    bubble.className = "faculty-chatbot__bubble";
    if (content && typeof content === "object") {
      const values = content.data
        ? Object.entries(content.data).map(([label, value]) => `${label}: ${value}`).join("\n")
        : "";
      appendReportContent(
        bubble,
        [content.text || "Result", values].filter(Boolean).join("\n")
      );
    } else {
      appendReportContent(bubble, content);
    }
    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
  }

  function resetMessages() {
    messages.querySelectorAll(".faculty-chatbot__message").forEach((node) => node.remove());
    empty.hidden = false;
  }

  async function loadHistory() {
    if (historyLoaded) return;
    historyLoaded = true;
    try {
      const response = await fetch(root.dataset.historyUrl, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || "Unable to load history.");
      data.history.forEach((item) => addMessage(item.role, item.content));
    } catch (error) {
      status.textContent = error.message;
    }
  }

  async function submitQuery(query) {
    if (busy || !query) return;
    busy = true;
    addMessage("user", query);
    input.value = "";
    input.style.height = "auto";
    send.disabled = true;
    status.textContent = "Checking your permitted ERP data…";

    try {
      const response = await fetch(root.dataset.chatUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || "The assistant could not respond.");
      addMessage("assistant", data.response);
      status.textContent = "";
    } catch (error) {
      addMessage("assistant", error.message || "Something went wrong. Please try again.");
      status.textContent = "";
    } finally {
      busy = false;
      send.disabled = false;
      input.focus();
    }
  }

  toggle.addEventListener("click", () => setOpen(true));
  close.addEventListener("click", () => setOpen(false));
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitQuery(input.value.trim());
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  input.addEventListener("input", () => {
    resizeInput();
  });
  if (questionToggle && questionPanel) {
    questionToggle.addEventListener("click", () => {
      setQuestionsOpen(questionPanel.hidden);
    });
    questionClose.addEventListener("click", () => {
      setQuestionsOpen(false);
      questionToggle.focus();
    });
    questionSearch.addEventListener("input", renderQuestions);
  }
  root.querySelectorAll("[data-chat-suggestion]").forEach((button) => {
    button.addEventListener("click", () => submitQuery(button.dataset.chatSuggestion));
  });
  const prepareTemplateInput = (template, selectedPlaceholder = "") => {
    input.value = template;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 116)}px`;
    input.focus();
    const placeholderStart = selectedPlaceholder
      ? template.indexOf(selectedPlaceholder)
      : -1;
    if (placeholderStart >= 0) {
      input.setSelectionRange(
        placeholderStart,
        placeholderStart + selectedPlaceholder.length
      );
      return;
    }
    input.setSelectionRange(template.length, template.length);
  };
  root.querySelectorAll("[data-chat-template]").forEach((button) => {
    button.addEventListener("click", () => {
      const template = button.dataset.chatTemplate || "";
      const selectedPlaceholder = button.dataset.chatSelectPlaceholder || "";
      prepareTemplateInput(template, selectedPlaceholder);
      status.textContent = "Replace the subject code, batch, and section placeholders, then send.";
    });
  });
  root.querySelectorAll("[data-chat-template-prefix]").forEach((button) => {
    button.addEventListener("click", () => {
      const templatePrefix = button.dataset.chatTemplatePrefix || "";
      prepareTemplateInput(templatePrefix);
      status.textContent = "Enter the student's 12-digit register number, then send.";
    });
  });
  clear.addEventListener("click", async () => {
    if (busy || !window.confirm("Clear this chatbot conversation?")) return;
    try {
      const response = await fetch(root.dataset.historyUrl, {
        method: "DELETE",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrfToken, Accept: "application/json" },
      });
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || "Unable to clear history.");
      resetMessages();
      status.textContent = "Conversation cleared.";
    } catch (error) {
      status.textContent = error.message;
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || panel.hidden) return;
    if (questionPanel && !questionPanel.hidden) {
      setQuestionsOpen(false);
      questionToggle.focus();
      return;
    }
    setOpen(false);
  });
})();
