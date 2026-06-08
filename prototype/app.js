const pages = {
  dashboard: {
    title: "工作台",
    subtitle: "多角色协同、待办审批、项目经营指标总览",
  },
  project: {
    title: "立项管理",
    subtitle: "合同上传、OCR/NLP 提取、PDF 校验与立项审批",
  },
  invoice: {
    title: "开票回款",
    subtitle: "发票识别、开票登记、回款记录与应收款计算",
  },
  close: {
    title: "结项管理",
    subtitle: "结项申请、财务审核、管理员归档和撤回结项",
  },
  report: {
    title: "查询报表",
    subtitle: "按项目和时间汇总开票回款，支持 Excel/PDF 导出",
  },
  system: {
    title: "系统管理",
    subtitle: "用户、角色、数据字典、审批流和操作日志",
  },
};

const roles = {
  admin: {
    name: "管理员",
    username: "admin",
    home: "dashboard",
    pages: ["dashboard", "project", "invoice", "close", "report", "system"],
    hint: "管理员：可审核立项、查看全量数据并维护系统配置。",
    notify: "审批通知：4 个立项待审核，2 个结项待归档。",
    noticeLabel: "审批通知 6",
    todoCount: "6",
    flow: ["商务提交", "管理员审核", "项目已立项"],
  },
  business: {
    name: "商务",
    username: "business01",
    home: "dashboard",
    pages: ["dashboard", "project", "report"],
    hint: "商务：可进行立项登记、合同校验和提交立项审批。",
    notify: "审批通知：3 个草稿待补充，5 份合同待校验。",
    noticeLabel: "合同待办 8",
    todoCount: "8",
    flow: ["上传 Word 合同", "PDF 合同校验", "提交立项审核"],
  },
  finance: {
    name: "财务",
    username: "finance01",
    home: "dashboard",
    pages: ["dashboard", "invoice", "close", "report"],
    hint: "财务：可登记开票回款并审核结项申请。",
    notify: "审批通知：2 个结项待审核，1 张发票触发审批。",
    noticeLabel: "财务待办 3",
    todoCount: "3",
    flow: ["发票 OCR", "回款登记", "结项财务审核"],
  },
  pm: {
    name: "项目经理",
    username: "pm01",
    home: "dashboard",
    pages: ["dashboard", "project", "close", "report"],
    hint: "项目经理：可跟踪项目状态并提交结项申请。",
    notify: "审批通知：2 个项目待提交结项，1 个申请被驳回需补充。",
    noticeLabel: "项目待办 3",
    todoCount: "3",
    flow: ["查看项目进度", "上传验收报告", "提交结项申请"],
  },
};

let currentRole = null;

const body = document.body;
const loginScreen = document.querySelector("#login-screen");
const appShell = document.querySelector("#app-shell");
const loginForm = document.querySelector("#login-form");
const loginRole = document.querySelector("#login-role");
const loginName = document.querySelector("#login-name");
const loginRoleCards = document.querySelectorAll("[data-login-role]");
const navItems = document.querySelectorAll(".nav-item");
const pageEls = document.querySelectorAll(".page");
const rolePanels = document.querySelectorAll("[data-role-panel]");
const pageTitle = document.querySelector("#page-title");
const pageSubtitle = document.querySelector("#page-subtitle");
const activeRoleBadge = document.querySelector("#active-role-badge");
const roleSelect = document.querySelector("#role-select");
const todoBadge = document.querySelector("#todo-badge");
const notifyBtn = document.querySelector("#notify-btn");
const miniFlow = document.querySelector(".mini-flow");
const toast = document.querySelector("#toast");

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
}

function roleAllows(role, list) {
  return list
    .split(",")
    .map((item) => item.trim())
    .includes(role);
}

function canOpenPage(pageId) {
  return currentRole && roles[currentRole].pages.includes(pageId);
}

function setRoleCard(role) {
  loginRoleCards.forEach((card) => {
    card.classList.toggle("active", card.dataset.loginRole === role);
  });
}

function syncLoginRole(role) {
  loginRole.value = role;
  loginName.value = roles[role].username;
  setRoleCard(role);
}

function applyRoleVisibility() {
  const allowedPages = roles[currentRole].pages;

  navItems.forEach((item) => {
    const allowed = allowedPages.includes(item.dataset.page);
    item.hidden = !allowed;
    item.classList.toggle("active", allowed && item.dataset.page === roles[currentRole].home);
  });

  document.querySelectorAll("[data-roles]").forEach((element) => {
    element.hidden = !roleAllows(currentRole, element.dataset.roles);
  });

  document.querySelectorAll("[data-page-jump]").forEach((button) => {
    const targetPage = button.dataset.pageJump;
    const roleAllowed = !button.dataset.roles || roleAllows(currentRole, button.dataset.roles);
    button.hidden = !roleAllowed || !canOpenPage(targetPage);
  });

  rolePanels.forEach((panel) => {
    const active = panel.dataset.rolePanel === currentRole;
    panel.hidden = !active;
    panel.classList.toggle("active", active);
  });

  roleSelect.value = currentRole;
  if (activeRoleBadge) {
    activeRoleBadge.textContent = `当前身份：${roles[currentRole].name}`;
  }
  if (todoBadge) {
    todoBadge.textContent = roles[currentRole].todoCount;
  }
  if (notifyBtn) {
    notifyBtn.textContent = roles[currentRole].noticeLabel;
  }
  if (miniFlow) {
    miniFlow.innerHTML = roles[currentRole].flow
      .map((step, index) => `<li class="${index === 0 ? "done" : index === 1 ? "current" : ""}">${step}</li>`)
      .join("");
  }
}

function switchPage(pageId) {
  const page = pages[pageId];
  if (!page) return;

  if (!canOpenPage(pageId)) {
    showToast(`${roles[currentRole].name}无权访问“${page.title}”。`);
    return;
  }

  navItems.forEach((item) => item.classList.toggle("active", item.dataset.page === pageId));
  pageEls.forEach((el) => el.classList.toggle("active", el.id === pageId));
  pageTitle.textContent = page.title;
  pageSubtitle.textContent = page.subtitle;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function loginAs(role) {
  currentRole = role;
  body.classList.add("logged-in");
  loginScreen.hidden = true;
  appShell.hidden = false;
  appShell.setAttribute("aria-hidden", "false");
  applyRoleVisibility();
  switchPage(roles[role].home);
  showToast(`${roles[role].name}已登录，只展示当前身份可访问的功能。`);
}

function logout() {
  currentRole = null;
  body.classList.remove("logged-in");
  loginScreen.hidden = false;
  appShell.hidden = true;
  appShell.setAttribute("aria-hidden", "true");
  syncLoginRole(loginRole.value || "admin");
}

loginRoleCards.forEach((card) => {
  card.addEventListener("click", () => syncLoginRole(card.dataset.loginRole));
});

loginRole.addEventListener("change", (event) => syncLoginRole(event.target.value));

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loginAs(loginRole.value);
});

navItems.forEach((item) => {
  item.addEventListener("click", () => switchPage(item.dataset.page));
});

document.querySelectorAll("[data-page-jump]").forEach((button) => {
  button.addEventListener("click", () => switchPage(button.dataset.pageJump));
});

roleSelect.addEventListener("change", (event) => {
  loginAs(event.target.value);
});

document.querySelector("#logout-btn").addEventListener("click", logout);

notifyBtn.addEventListener("click", () => {
  showToast(roles[currentRole].notify);
});

document.querySelector("#simulate-contract-ocr").addEventListener("click", () => {
  document.querySelector("#project-name").value = "OCR 发票与合同识别平台";
  document.querySelector("#customer-name").value = "北京启明数科有限公司";
  document.querySelector("#contract-amount").value = "680000";
  document.querySelector("#contract-no").value = "HT-2026-0068";
  document.querySelector("#sign-date").value = "2026-06-08";
  showToast("已模拟完成合同 OCR/NLP 提取，低置信度字段仍可人工修正。");
});

document.querySelector("#simulate-invoice-ocr").addEventListener("click", () => {
  document.querySelector("#invoice-amount").value = "188000";
  document.querySelector("#invoice-date").value = "2026-06-08";
  document.querySelector("#invoice-no").value = "044002600688";
  document.querySelector("#buyer-name").value = "北京启明数科有限公司";
  document.querySelector("#seller-name").value = "智能项目管理系统供应商";
  showToast("已模拟识别发票号码、金额、日期、购方和销方。");
});

syncLoginRole("admin");
appShell.hidden = true;
