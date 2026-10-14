let currentTab = 'dashboard';
let currentView = 'dashboard';
let teacherInfo = null;
let classesCache = [];
let currentClassId = null;
let currentTeamId = null;

function $(id) { return document.getElementById(id); }
function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return document.querySelectorAll(sel); }

function showToast(msg, duration) {
  duration = duration || 2000;
  const t = $('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._hide);
  t._hide = setTimeout(function() { t.classList.add('hidden'); }, duration);
}

function escapeHtml(text) {
  if (!text) return '';
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

function imgUrl(path) {
  if (!path) return '';
  return path.indexOf('http') === 0 ? path : '/' + path;
}

function formatDate(d) {
  if (!d) return '';
  const date = new Date(d);
  return date.getFullYear() + '-' + String(date.getMonth()+1).padStart(2,'0') + '-' + String(date.getDate()).padStart(2,'0');}

function formatDateTime(d) {
  if (!d) return '';
  var date = new Date(d);
  return date.getFullYear() + '-' + String(date.getMonth()+1).padStart(2,'0') + '-' + String(date.getDate()).padStart(2,'0') + ' ' + String(date.getHours()).padStart(2,'0') + ':' + String(date.getMinutes()).padStart(2,'0');
}

function showPage(pageId) {
  qsa('.page').forEach(function(p) { p.classList.add('hidden'); });
  $(pageId).classList.remove('hidden');
}

function getContentArea() {
  return qs('#page-content');
}

$('login-btn').addEventListener('click', async function() {
  const name = $('login-name').value.trim();
  const password = $('login-password').value;
  if (!name || !password) {
    showToast('请输入教师姓名和密码');
    return;
  }
  $('login-btn').disabled = true;
  $('login-btn').textContent = '登录中...';
  try {
    const res = await authApi.login(name, password);
    setToken(res.access_token);
    teacherInfo = { id: res.teacher_id, name: res.name, school: res.school || '' };
    showToast('登录成功');
    enterMainApp();
  } catch (e) {
    showToast(e.message);
  } finally {
    $('login-btn').disabled = false;
    $('login-btn').textContent = '教师登录';
  }
});

$('admin-login-btn').addEventListener('click', async function() {
  const username = $('admin-username').value.trim();
  const password = $('admin-password').value;
  if (!username || !password) { showToast('请输入管理员账号和密码'); return; }
  this.disabled = true;
  try {
    const result = await adminApi.login(username, password);
    adminToken = result.access_token;
    $('admin-password').value = '';
    $('admin-login-form').classList.add('hidden');
    $('admin-teacher-form').classList.remove('hidden');
    await refreshAdminTeachers();
  } catch (e) {
    showToast(e.message);
  } finally {
    this.disabled = false;
  }
});

async function refreshAdminTeachers() {
  const teachers = await adminApi.teachers();
  $('admin-teacher-list').innerHTML = '<div style="font-weight:600;margin:16px 0 8px;">现有教师</div>' +
    teachers.map(t => '<div style="padding:6px 0;">' + escapeHtml(t.name) +
      (t.school ? ' · ' + escapeHtml(t.school) : '') + '</div>').join('');
}

$('admin-add-teacher-btn').addEventListener('click', async function() {
  const name = $('admin-teacher-name').value.trim();
  const school = $('admin-teacher-school').value.trim();
  const password = $('admin-teacher-password').value;
  const confirmation = $('admin-teacher-confirm').value;
  if (!name || password.length < 12) { showToast('请填写姓名和至少12位密码'); return; }
  if (password !== confirmation) { showToast('两次密码不一致'); return; }
  this.disabled = true;
  try {
    await adminApi.addTeacher(name, school, password);
    $('admin-teacher-name').value = '';
    $('admin-teacher-school').value = '';
    $('admin-teacher-password').value = '';
    $('admin-teacher-confirm').value = '';
    await refreshAdminTeachers();
    showToast('教师已创建');
  } catch (e) {
    showToast(e.message);
  } finally {
    this.disabled = false;
  }
});

function adminLogout() {
  adminToken = '';
  $('admin-login-form').classList.remove('hidden');
  $('admin-teacher-form').classList.add('hidden');
  showLoginPage();
}

function enterMainApp() {
  var t = document.getElementById('tab-bar');
  if (t) t.style.display = '';
  showPage('main-page');
  // Activate 我的班级 tab
  qsa('.tab-item').forEach(function(item) { item.classList.remove('active'); });
  var dt = document.querySelector('.tab-item[data-tab="dashboard"]');
  if (dt) dt.classList.add('active');
  currentTab = 'dashboard';
  renderDashboard();
}

qsa('.tab-item').forEach(function(item) {
  item.addEventListener('click', function() {
    qsa('.tab-item').forEach(function(t) { t.classList.remove('active'); });
    item.classList.add('active');
    currentTab = item.dataset.tab;
    if (currentTab === 'home') renderHomeTab();
    else if (currentTab === 'dashboard') renderDashboard();
    else if (currentTab === 'profile') renderProfile();
  });
});

async function renderDashboard() {
  currentView = 'dashboard';
  const area = getContentArea();
  area.innerHTML = '<div class="top-nav"><h1>我的班级</h1><button class="right-action" onclick="showCreateClassModal()">+ 创建班级</button></div><div class="content-area" id="class-list"><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div></div>';
  try {
    classesCache = await classApi.list();
    const list = $('class-list');
    if (classesCache.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="icon">📚</div><p>还没有班级，点击右上角创建</p><button class="btn-primary mt-16" style="width:auto;padding:0 24px;" onclick="showCreateClassModal()">创建第一个班级</button></div>';
      return;
    }
    list.innerHTML = classesCache.map(function(c) {
      return '<div class="card fade-in" onclick="showClassDetail(' + c.id + ')">' +
        '<div class="card-header"><span class="card-title">' + escapeHtml(c.name) + '</span><span class="card-badge">' + escapeHtml(c.grade || '未设置年级') + '</span></div>' +
        '<div class="card-stats">' +
        '<div class="stat-item"><span class="stat-value">' + c.team_count + '</span><span class="stat-label">小组</span></div>' +
        '<div class="stat-item"><span class="stat-value">' + c.student_count + '</span><span class="stat-label">学生</span></div>' +
        '</div>' +
        (c.description ? '<div class="card-subtitle">' + escapeHtml(c.description) + '</div>' : '') +
        '</div>';
    }).join('');
  } catch (e) {
    $('class-list').innerHTML = '<div class="empty-state"><p>⚠️ ' + e.message + '</p></div>';
  }
}

function generateYearOptions() {
  var currentYear = 2026;
  var options = "";
  for (var y = 2018; y <= 2030; y++) {
    var selected = (y === 2024) ? " selected" : "";
    options += "<option value=\"" + y + "级\"" + selected + ">" + y + "级</option>";
  }
  return options;
}

function showCreateClassModal() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'create-class-modal';
  overlay.innerHTML = '<div class="modal-content"><div class="modal-header"><h3>创建班级</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
    '<div class="form-group"><label>班级名称</label><input class="input-field" id="new-class-name" placeholder="例如：2024级9班"></div>' +
    '<div class="form-group"><label>年级</label><select class="input-field" id="new-class-grade">' + generateYearOptions() + '</select></div>' +
    '<div class="form-group"><label>描述（选填）</label><textarea id="new-class-desc" placeholder="可填写班级简介"></textarea></div>' +
    '<button class="btn-primary" onclick="submitCreateClass()">创建</button></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
}

async function submitCreateClass() {
  const name = $('new-class-name').value.trim();
  if (!name) { showToast('请输入班级名称'); return; }
  // 从班级名称自动提取年级，如 "2026级3班" -> "2026级"
  let grade = "";
  const match = name.match(/^(\d{4}\u7ea7)/);
  if (match) {
    grade = match[1];
  } else {
    grade = $('new-class-grade').value;
  }
  try {
    await classApi.create({
      name: name,
      grade: grade,
      description: $('new-class-desc').value.trim(),
    });
    $('create-class-modal').remove();
    showToast('班级创建成功');
    renderDashboard();
  } catch (e) { showToast(e.message); }
}

async function showClassDetail(classId) {
  currentView = 'class-detail';
  currentClassId = classId;
  const area = getContentArea();
  area.innerHTML = '<div class="top-nav"><button class="back-btn" onclick="renderDashboard()">← 返回</button><h1>班级详情</h1><button class="right-action" onclick="showClassActions()">⋮</button></div><div class="content-area" id="class-detail-content"><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div></div>';
  await renderClassDetail();
}

async function renderClassDetail() {
  const content = $('class-detail-content');
  try {
    const cls = await classApi.get(currentClassId);
    const teams = await classApi.listTeams(currentClassId);
    const students = await classApi.listStudents(currentClassId);
    content.innerHTML =
      '<div class="card" style="cursor:default;">' +
      '<div class="card-header"><span class="card-title">' + escapeHtml(cls.name) + '</span><span class="card-badge">' + escapeHtml(cls.grade || '—') + '</span></div>' +
      '<div class="card-stats">' +
      '<div class="stat-item"><span class="stat-value">' + teams.length + '</span><span class="stat-label">小组</span></div>' +
      '<div class="stat-item"><span class="stat-value">' + students.length + '</span><span class="stat-label">学生</span></div>' +
      '</div>' +
      (cls.description ? '<p style="font-size:14px;color:#636366;margin-top:8px;">' + escapeHtml(cls.description) + '</p>' : '') +
      '</div>' +
      '<div class="section-header"><h3>小组 (' + teams.length + ')</h3><button class="action" onclick="showCreateTeamModal()">+ 新建</button></div>' +
      '<div id="teams-list">' +
      (teams.length === 0 ? '<div class="empty-state"><p>还没有小组，点击右上角新建</p></div>' :
        teams.map(function(t) {
          return '<div class="card fade-in" onclick="showTeamDetail(' + t.id + ')">' +
            '<div class="card-header"><span class="card-title">' + escapeHtml(t.name) + '</span><span class="card-badge">' + t.member_count + '人</span></div>' +
            '<div class="card-stats"><div class="stat-item"><span class="stat-value">' + t.practice_count + '</span><span class="stat-label">实践</span></div></div>' +
            '</div>';
        }).join('')
      ) +
      '</div>' +
      '<div class="section-header mt-16"><h3>导入学生</h3></div>' +
      '<div style="margin-bottom:8px;">' +
      '<a href="/uploads/学生导入模板.xlsx" download class="btn-secondary" style="text-decoration:none;display:inline-flex;align-items:center;gap:6px;">📥 下载导入模板</a>' +
      '</div>' +

      '<div class="card" style="cursor:default;border:1.5px dashed var(--primary);background:var(--primary-light);" onclick="document.getElementById(\'excel-input\').click()">' +
      '<div style="text-align:center;padding:20px;">' +
      '<div style="font-size:36px;margin-bottom:8px;">📊</div>' +
      '<p style="font-size:15px;color:var(--primary-dark);font-weight:600;">通过 Excel 导入学生数据</p>' +
      '<p style="font-size:12px;color:var(--primary);margin-top:4px;opacity:0.8;">表头: 姓名, 学号, 年级, 出生年月, 小组, 职责</p>' +
      '</div>' +
      '<input type="file" id="excel-input" accept=".xlsx,.xls" style="display:none" onchange="importExcel(event)">' +
      '</div>';
  } catch (e) {
    content.innerHTML = '<div class="empty-state"><p>⚠️ ' + e.message + '</p></div>';
  }
}

function showClassActions() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content">' +
    '<div class="modal-header"><h3>班级操作</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
    '<div class="profile-menu-item" onclick="if(confirm(\'确定删除此班级？\')){deleteClass()}">🗑️ 删除班级</div>' +
    '</div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
}

async function deleteClass() {
  try {
    await classApi.delete(currentClassId);
    showToast('班级已删除');
    document.querySelector('.modal-overlay').remove();
    renderDashboard();
  } catch (e) { showToast(e.message); }
}

function showCreateTeamModal() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content">' +
    '<div class="modal-header"><h3>新建小组</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
    '<div class="form-group"><label>小组名称</label><input class="input-field" id="new-team-name" placeholder="例如：第一组 / 探索组"></div>' +
    '<button class="btn-primary" onclick="submitCreateTeam()">创建</button></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
}

async function submitCreateTeam() {
  const name = $('new-team-name').value.trim();
  if (!name) { showToast('请输入小组名称'); return; }
  try {
    await classApi.createTeam(currentClassId, { name: name });
    document.querySelector('.modal-overlay').remove();
    showToast('小组创建成功');
    renderClassDetail();
  } catch (e) { showToast(e.message); }
}

async function importExcel(event) {
  const file = event.target.files[0];
  if (!file) return;
  showToast('正在导入...');
  try {
    const res = await classApi.importExcel(currentClassId, file);
    showToast('导入成功: ' + res.students_imported + '名学生, ' + res.teams_created + '个小组');
    renderClassDetail();
  } catch (e) { showToast('导入失败: ' + e.message); }
  event.target.value = '';
}

async function showTeamDetail(teamId) {
  currentView = 'team-detail';
  currentTeamId = teamId;
  const area = getContentArea();
  area.innerHTML = '<div class="top-nav"><button class="back-btn" onclick="showClassDetail(' + currentClassId + ')">← 返回</button><h1>小组详情</h1><button class="right-action" onclick="showTeamActions()">⋮</button></div><div class="content-area" id="team-detail-content"><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div></div>';
  await renderTeamDetail();
}

async function renderTeamDetail() {
  const content = $('team-detail-content');
  try {
    const team = await teamApi.get(currentTeamId);
    const members = await teamApi.members(currentTeamId);
    const practices = await practiceApi.listByTeam(currentTeamId);
    content.innerHTML =
      '<div class="card" style="cursor:default;">' +
      '<div class="card-header"><span class="card-title">' + escapeHtml(team.name) + '</span></div>' +
      '<div class="card-stats">' +
      '<div class="stat-item"><span class="stat-value">' + team.member_count + '</span><span class="stat-label">成员</span></div>' +
      '<div class="stat-item"><span class="stat-value">' + team.practice_count + '</span><span class="stat-label">实践</span></div>' +
      '</div>' +
      '<div style="display:flex;gap:8px;margin-top:12px;">' +
      '<button class="btn-secondary" style="flex:1;justify-content:center;" onclick="showTeamQRCode(' + currentTeamId + ')"><span>📱</span> 二维码</button>' +
      '<button class="btn-secondary" style="flex:1;justify-content:center;" onclick="shareTeamUrl(' + currentTeamId + ')"><span>🔗</span> 分享</button>' +
      '</div>' +
      '</div>' +
      '<div class="section-header"><h3>成员 (' + members.length + ')</h3><button class="action" onclick="showAddMemberModal()">+ 分配</button></div>' +
      '<div class="card" style="cursor:default;" id="members-list">' +
      (members.length === 0 ? '<div class="empty-state" style="padding:24px;"><p>还没有成员</p></div>' :
        members.map(function(m) {
          return '<div class="member-item" onclick="showStudentDetail(' + m.id + ')">' +
            '<div class="member-avatar">' + escapeHtml(m.name.charAt(0)) + '</div>' +
            '<div class="member-info">' +
            '<div class="member-name">' + escapeHtml(m.name) + '</div>' +
            '<div class="member-role">' + escapeHtml(m.role || '未分配职责') + '</div>' +
            '</div>' +
            '<span class="member-tag">' + escapeHtml(m.student_no || '—') + '</span>' +
            '</div>';
        }).join('')
      ) +
      '</div>' +
      '<div class="section-header mt-16"><h3>实践记录 (' + practices.length + ')</h3><button class="action" onclick="showCreatePracticeModal()">+ 记录</button></div>' +
      '<div id="practices-list">' +
      (practices.length === 0 ? '<div class="empty-state"><p>还没有实践记录，点击右上角记录</p></div>' :
        practices.map(function(p) {
          return '<div class="practice-item fade-in" onclick="showPracticeDetail(' + p.id + ')">' +
            (p.images && p.images.length > 0 ? '<div class="practice-images" style="margin-top:0;margin-bottom:8px;">' + p.images.slice(0,3).map(function(img) { return '<img src=\"' + imgUrl(img) + '" onclick="showImageLightbox(this.src)" style="width:72px;height:72px;border-radius:8px;object-fit:cover;">'; }).join('') + '</div>' : '') +
            '<div class="practice-title">' + escapeHtml(p.title) + '</div>' +
            '<div class="practice-meta">' + formatDate(p.created_at) + ' · ' + p.member_count + '人参与</div>' +
            '<button class="btn-secondary" style="margin:8px 0;" onclick="event.stopPropagation();togglePracticePublication(' + p.id + ',' + (!p.published) + ')">' + (p.published ? '取消公开' : '公开作品') + '</button>' +
            '<div class="practice-content">' + escapeHtml(p.content) + '</div>' +
            (p.ai_summary ? '<div class="practice-analysis">💡 ' + escapeHtml(p.ai_summary) + '</div>' : '') +
            '</div>';
        }).join('')
      ) +
      '</div>';
  } catch (e) {
    content.innerHTML = '<div class="empty-state"><p>⚠️ ' + e.message + '</p></div>';
  }
}

async function togglePracticePublication(practiceId, published) {
  try {
    await practiceApi.setPublication(practiceId, published);
    showToast(published ? '作品已公开' : '作品已取消公开');
    renderTeamDetail();
  } catch (e) {
    showToast(e.message);
  }
}

function showTeamActions() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content">' +
    '<div class="modal-header"><h3>小组操作</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
    '<div class="profile-menu-item" onclick="showTeamQRCode(' + currentTeamId + ');this.closest(\'.modal-overlay\').remove()">📱 查看二维码</div>' +
    '<div class="profile-menu-item" onclick="if(confirm(\'确定删除此小组？\')){deleteTeam()}">🗑️ 删除小组</div>' +
    '</div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
}

async function deleteTeam() {
  try {
    await teamApi.delete(currentTeamId);
    showToast('小组已删除');
    document.querySelector('.modal-overlay').remove();
    showClassDetail(currentClassId);
  } catch (e) { showToast(e.message); }
}

async function showTeamQRCode(teamId) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content"><div class="modal-header"><h3>小组二维码</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div><div class="qrcode-container" id="qrcode-container"><p>加载中...</p></div></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  try {
    const res = await teamApi.qrcode(teamId);
    $('qrcode-container').innerHTML = '<img src="data:image/png;base64,' + res.qr_base64 + '" alt="二维码"><p>扫码查看小组实践内容</p><button class="btn-primary mt-16" style="width:auto;padding:0 24px;" onclick="shareTeamUrl(' + teamId + ')">🔗 分享链接</button>';
  } catch (e) {
    $('qrcode-container').innerHTML = '<p>生成失败: ' + e.message + '</p>';
  }
}

function showAddMemberModal() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content">' +
    '<div class="modal-header"><h3>分配成员到小组</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
    '<div id="unassigned-students-list"><p>加载中...</p></div></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  loadUnassignedStudents();
}

async function loadUnassignedStudents() {
  try {
    const students = await classApi.listStudents(currentClassId);
    const unassigned = students.filter(function(s) { return s.team_id === null || s.team_id !== currentTeamId; });
    const list = $('unassigned-students-list');
    if (unassigned.length === 0) {
      list.innerHTML = '<div class="empty-state" style="padding:24px;"><p>没有可分配的学生</p></div>';
      return;
    }
    list.innerHTML = unassigned.map(function(s) {
      return '<div class="member-item" style="cursor:pointer;" onclick="assignStudentToTeam(' + s.id + ')">' +
        '<div class="member-avatar">' + escapeHtml(s.name.charAt(0)) + '</div>' +
        '<div class="member-info"><div class="member-name">' + escapeHtml(s.name) + '</div><div class="member-role">' + (s.role || '未分配职责') + '</div></div>' +
        '<span style="color:#4F6EF7;font-size:14px;">分配</span>' +
        '</div>';
    }).join('');
  } catch (e) {
    $('unassigned-students-list').innerHTML = '<p>' + e.message + '</p>';
  }
}

async function assignStudentToTeam(studentId) {
  try {
    await studentApi.update(studentId, { team_id: currentTeamId });
    showToast('已分配');
    document.querySelector('.modal-overlay').remove();
    renderTeamDetail();
  } catch (e) { showToast(e.message); }
}

async function showStudentDetail(studentId) {
  currentView = 'student-detail';
  const area = getContentArea();
  area.innerHTML = '<div class="top-nav"><button class="back-btn" onclick="showTeamDetail(' + currentTeamId + ')">← 返回</button><h1>学生详情</h1></div><div class="content-area" id="student-detail-content"><div class="skeleton skeleton-card"></div></div>';
  try {
    const s = await studentApi.get(studentId);
    $('student-detail-content').innerHTML =
      '<div class="card fade-in" style="cursor:default;">' +
      '<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">' +
      '<div class="member-avatar" style="width:60px;height:60px;font-size:26px;">' + escapeHtml(s.name.charAt(0)) + '</div>' +
      '<div><div style="font-size:22px;font-weight:700;">' + escapeHtml(s.name) + '</div>' +
      '<div style="font-size:14px;color:#636366;margin-top:2px;">' + escapeHtml(s.student_no || '无学号') + '</div></div>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;padding-top:16px;border-top:0.5px solid var(--gray-2);">' +
      '<div><div style="font-size:12px;color:#8E8E93;text-transform:uppercase;letter-spacing:0.5px;">年级</div><div style="font-size:16px;font-weight:600;margin-top:4px;">' + escapeHtml(s.grade || '未设置') + '</div></div>' +
      '<div><div style="font-size:12px;color:#8E8E93;text-transform:uppercase;letter-spacing:0.5px;">出生年月</div><div style="font-size:16px;font-weight:600;margin-top:4px;">' + (s.birth_date ? formatDate(s.birth_date) : '未设置') + '</div></div>' +
      '<div style="grid-column:1/-1;"><div style="font-size:12px;color:#8E8E93;text-transform:uppercase;letter-spacing:0.5px;">小组职责</div><div style="font-size:16px;font-weight:600;margin-top:4px;">' + escapeHtml(s.role || '未分配') + '</div></div>' +
      '</div>' +
      '<button class="btn-secondary" style="margin-top:16px;" onclick="resetStudentLoginCode(' + s.id + ')">生成学生登录口令</button>' +
      '</div>';
  } catch (e) {
    $('student-detail-content').innerHTML = '<p>⚠️ ' + e.message + '</p>';
  }
}

async function resetStudentLoginCode(studentId) {
  try {
    const result = await studentApi.resetLoginCode(studentId);
    window.prompt('请复制并私下告知学生，关闭后无法再次查看：', result.code);
  } catch (e) {
    showToast(e.message);
  }
}

function showCreatePracticeModal() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content">' +
    '<div class="modal-header"><h3>记录实践活动</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
    '<div class="form-group"><label>活动标题</label><input class="input-field" id="practice-title" placeholder="例如：植物观察实验"></div>' +
    '<div class="form-group"><label>活动内容</label><textarea id="practice-content" placeholder="详细描述活动过程..."></textarea></div>' +
    '<div class="form-group"><label>拍照上传</label>' +
    '<div class="file-upload-area" onclick="document.getElementById(\'practice-files\').click()"><div style="font-size:32px;margin-bottom:6px;">📸</div>点击拍照或选择照片</div>' +
    '<input type="file" id="practice-files" accept="image/*" multiple style="display:none" onchange="previewPracticeImages(event)">' +
    '<div class="preview-images" id="practice-image-previews"></div></div>' +
    '<div class="form-group" id="member-works-section"><label>成员分工</label><div id="member-works-list"></div></div>' +
    '<button class="btn-primary" onclick="submitPractice()">提交并生成参考分析</button></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  loadMemberWorksForm();
}

let practiceFiles = [];

function previewPracticeImages(event) {
  var files = Array.from(event.target.files);
  if (files.length > 9) {
    showToast('\u6700\u591a\u53ea\u80fd\u4e0a\u4f209\u5f20\u56fe\u7247');
    files = files.slice(0, 9);
  }
  practiceFiles = files;
  var container = $('practice-image-previews');
  container.innerHTML = practiceFiles.map(function(f) {
    return '<img src="' + URL.createObjectURL(f) + '">';
  }).join('');
}

async function loadMemberWorksForm() {
  const container = $('member-works-list');
  try {
    const members = await teamApi.members(currentTeamId);
    if (members.length === 0) {
      container.innerHTML = '<p style="font-size:13px;color:#8E8E93;">请先分配成员到小组</p>';
      return;
    }
    container.innerHTML = members.map(function(m) {
      return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">' +
        '<span style="font-size:14px;min-width:48px;">' + escapeHtml(m.name) + '</span>' +
        '<input class="input-field" style="flex:1;margin-bottom:0;height:40px;" placeholder="' + escapeHtml(m.role || '填写分工内容') + '" data-student-id="' + m.id + '">' +
        '</div>';
    }).join('');
  } catch (e) {
    container.innerHTML = '<p style="font-size:13px;color:#FF3B30;">' + e.message + '</p>';
  }
}

async function submitPractice() {
  const title = $('practice-title').value.trim();
  const content = $('practice-content').value.trim();
  if (!title) { showToast('请输入活动标题'); return; }

  const workInputs = qsa('#member-works-list input');
  const memberWorks = Array.from(workInputs).map(function(input) {
    return { student_id: parseInt(input.dataset.studentId), work_description: input.value.trim() };
  }).filter(function(w) { return w.work_description; });

  showToast('正在提交并生成参考分析...');
  try {
    await practiceApi.create(currentTeamId, title, content, memberWorks, practiceFiles);
    document.querySelector('.modal-overlay').remove();
    showToast('实践记录已提交');
    renderTeamDetail();
  } catch (e) { showToast(e.message); }
}

async function showPracticeDetail(practiceId) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content" id="practice-detail-content"><div class="modal-header"><h3>实践详情</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div><p>加载中...</p></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });

  try {
    const p = await practiceApi.get(practiceId);
    const container = $('practice-detail-content');
    var teacherEval = p.evaluations ? p.evaluations.find(function(e) { return e.evaluator_role === 'teacher'; }) : null;
    container.innerHTML =
      '<div class="modal-header"><h3>实践详情</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
      '<div style="font-size:20px;font-weight:700;margin-bottom:6px;">' + escapeHtml(p.title) + '</div>' +
      '<div style="font-size:13px;color:#8E8E93;margin-bottom:16px;">📅 ' + formatDateTime(p.created_at) + '</div>' +
      (p.content ? '<div style="font-size:14px;color:#636366;margin-bottom:16px;white-space:pre-wrap;line-height:1.7;">' + escapeHtml(p.content) + '</div>' : '') +
      (p.images && p.images.length > 0 ? '<div class="practice-images">' + p.images.map(function(img) {
        return '<img src=\"' + imgUrl(img) + '" onclick="showImageLightbox(this.src)" style="width:80px;height:80px;border-radius:10px;object-fit:cover;">';
      }).join('') + '</div>' : '') +
      (p.member_records && p.member_records.length > 0 ?
        '<div style="margin-top:16px;padding:14px 16px;background:var(--gray-1);border-radius:12px;"><div style="font-size:14px;font-weight:700;margin-bottom:10px;">👥 成员分工</div>' +
        p.member_records.map(function(r) {
          return '<div style="font-size:14px;color:#636366;padding:6px 0;display:flex;gap:8px;"><span style="font-weight:600;color:var(--text);min-width:50px;">' + escapeHtml(r.student_name || '') + '</span><span>' + escapeHtml(r.work_description || '') + '</span></div>';
        }).join('') + '</div>' : '') +
      (p.ai_analysis ? '<div class="practice-analysis" style="margin-top:16px;"><strong>📊 参考分析</strong><br>' + escapeHtml(p.ai_analysis) + '</div>' : '') +
      (p.ai_summary ? '<div class="practice-analysis" style="margin-top:10px;"><strong>💡 参考摘要</strong><br>' + escapeHtml(p.ai_summary) + '</div>' : '') +
      '<div class="eval-section" style="margin-top:12px;padding-top:12px;border-top:0.5px solid var(--gray-2);">' +
      '<div style="font-size:14px;font-weight:500;margin-bottom:8px;">⭐ 教师评价</div>' +
      (teacherEval ?
        '<div style="background:#FFF9E6;padding:10px 12px;border-radius:8px;">' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">' +
        renderStars(teacherEval.score) +
        '<span style="font-size:15px;font-weight:600;color:#1C1C1E;">' + teacherEval.score + '分</span>' +
        '</div>' +
        (teacherEval.comment ? '<div style="font-size:14px;color:#636366;">' + escapeHtml(teacherEval.comment) + '</div>' : '') +
        '</div>' +
        '<button class="btn-secondary mt-8" style="font-size:13px;padding:4px 12px;" onclick="this.style.display=\'none\';document.getElementById(\'eval-form-' + practiceId + '\').classList.remove(\'hidden\')">✏️ 修改评价</button>'
        :
        ''
      ) +
      '<div id="eval-form-' + practiceId + '" class="' + (teacherEval ? 'hidden' : '') + '" style="margin-top:4px;">' +
      '<div id="eval-stars-' + practiceId + '">' +
      '<span onclick="setStarRating(' + practiceId + ',1)" style="cursor:pointer;font-size:24px;color:#E5E5EA;">★</span>' +
      '<span onclick="setStarRating(' + practiceId + ',2)" style="cursor:pointer;font-size:24px;color:#E5E5EA;">★</span>' +
      '<span onclick="setStarRating(' + practiceId + ',3)" style="cursor:pointer;font-size:24px;color:#E5E5EA;">★</span>' +
      '<span onclick="setStarRating(' + practiceId + ',4)" style="cursor:pointer;font-size:24px;color:#E5E5EA;">★</span>' +
      '<span onclick="setStarRating(' + practiceId + ',5)" style="cursor:pointer;font-size:24px;color:#E5E5EA;">★</span>' +
      ' <span style="font-size:14px;color:#636366;">0分</span></div>' +
      '<input type="hidden" id="eval-score-' + practiceId + '" value="0">' +
      '<textarea id="eval-comment-' + practiceId + '" placeholder="输入评语（选填）" style="width:100%;height:60px;border:1.5px solid #E5E5EA;border-radius:8px;padding:8px 12px;font-size:14px;margin-top:6px;resize:none;outline:none;"></textarea>' +
      '<button class="btn-primary" style="height:36px;font-size:14px;margin-top:6px;" onclick="submitEvaluation(' + practiceId + ')">提交评价</button>' +
      '</div>' +
      '</div>' +
      '<button class="btn-secondary mt-16" onclick="showEditPracticeModal(' + practiceId + ')" style="margin-right:6px;">✏️ 编辑</button>' +
      '<button class="btn-secondary mt-16" id="reanalyze-btn-' + practiceId + '" onclick="reanalyzePractice(' + practiceId + ')">🔄 重新生成参考分析</button>';
  } catch (e) {
    $('practice-detail-content').innerHTML = '<div class="modal-header"><h3>实践详情</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div><p>⚠️ ' + e.message + '</p>';
  }
}

async function renderProfile() {
  const area = getContentArea();
  const name = teacherInfo ? teacherInfo.name : '教师';
  const school = teacherInfo ? teacherInfo.school : '';
  area.innerHTML =
    '<div class="profile-header">' +
    '<div class="profile-avatar">👩‍🏫</div>' +
    '<div class="profile-name">' + escapeHtml(name) + '</div>' +
    (school ? '<div style="font-size:14px;opacity:0.85;margin-top:4px;">' + escapeHtml(school) + '</div>' : '') +
    '</div>' +
    '<div class="profile-menu">' +
    '<div class="profile-menu-item" onclick="renderDashboard()"><span>📚 我的班级</span><span style="color:#C7C7CC;">›</span></div>' +
    '<div class="profile-menu-item" onclick="showToast(\'版本 1.0.0\')"><span>ℹ️ 关于</span><span style="color:#C7C7CC;">›</span></div>' +
    '</div>' +
    '<div style="padding:16px;">' +
    '<button class="btn-primary" style="background:linear-gradient(135deg,#FF3B30 0%,#FF6B5B 100%);box-shadow:0 4px 14px rgba(255,59,48,0.25);" onclick="if(confirm(\'确定退出？\')){clearToken();showHomePage();}">退出登录</button>' +
    '</div>';
}

async function init() {
  showPage('loading-screen');
  var match = window.location.pathname.match(/^\/team\/(\d+)/);
  if (match) {
    renderTeamPublicPage(parseInt(match[1]));
    return;
  }
  var token = getToken();
  if (token) {
    try {
      var me = await authApi.me();
      if (me && me.id) {
        teacherInfo = { id: me.id, name: me.name, school: me.school || '' };
        enterMainApp();
        return;
      }
    } catch (e) {
      console.log('Token invalid, clearing');
    }
    clearToken();
  }
  showHomePage();
}

function showHomePage() {
  var t = document.getElementById('tab-bar');
  if (t) t.style.display = 'none';
  showPage("home-page");
  renderFeaturedPractices();
}

function showLoginPage() {
  showPage("login-page");
}

function renderFeaturedImages(images) {
  if (images && images.length > 0) {
    return '<div class="featured-card-images">' + images.map(function(img) { return '<img src=\"' + imgUrl(img) + '" onclick="showImageLightbox(this.src)" alt="">'; }).join('') + '</div>';
  }
  return '<div class="featured-card-images"><div class="placeholder-img">🔬</div></div>';
}

async function renderFeaturedPractices() {
  var container = $('featured-practices');
  if (!container) return;
  container.innerHTML = '<div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div>';
  try {
    var practices = await api('/practices/featured');
    if (practices.length === 0) {
      container.innerHTML = '<div class="empty-state"><div class="icon">🔬</div><p>暂无实践作品</p></div>';
      return;
    }
    container.innerHTML = practices.map(function(p) {
      return '<div class="featured-card fade-in" onclick="showHomePracticeDetail(' + p.id + ')">'
        + renderFeaturedImages(p.images)
        + '<div class="featured-card-body">'
        + '<div class="featured-card-title">' + escapeHtml(p.title) + '</div>'
        + '<div class="featured-card-meta">'
        + '<span>📚 ' + escapeHtml(p.class_name) + '</span>'
        + '<span>👥 ' + escapeHtml(p.team_name) + '</span>'
        + '<span>👤 ' + p.member_count + '人</span>'
        + '</div>'
        + '<div class="featured-card-summary">' + escapeHtml(p.content) + '</div>'
        + (p.ai_summary ? '<div class="featured-card-ai">💡 ' + escapeHtml(p.ai_summary) + '</div>' : '')
        + '<div class="featured-card-footer"><span>' + formatDate(p.created_at) + '</span></div>'
        + '</div></div>';
    }).join('');
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>加载失败,请重试</p></div>';
  }
}

async function showHomePracticeDetail(practiceId) {
  var overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content" id="home-detail-content"><p>加载中...</p></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  try {
    var p = await api('/practices/public/' + practiceId);
    var m = document.getElementById('home-detail-content');
    if (!m) { showToast('页面元素未找到'); return; }
    var imgHtml = '';
    if (p.images && p.images.length > 0) {
      imgHtml = '<div style="display:flex;gap:6px;margin-bottom:8px;overflow-x:auto;">' +
        p.images.map(function(i) { return '<img src=\"' + imgUrl(i) + '" onclick="showImageLightbox(this.src)" style="width:72px;height:72px;border-radius:8px;object-fit:cover;">'; }).join('') + '</div>';
    }
    var memHtml = '';
    if (p.member_records && p.member_records.length > 0) {
      memHtml = '<div style="margin-bottom:8px;"><div style="font-size:13px;font-weight:500;margin-bottom:4px;">成员分工</div>';
      for (var j = 0; j < p.member_records.length; j++) {
        var r = p.member_records[j];
        memHtml += '<div style="font-size:13px;padding:2px 0;"><b>' + escapeHtml(r.student_name || '') + '</b>: ' + escapeHtml(r.work_description || '') + '</div>';
      }
      memHtml += '</div>';
    }
    var h = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">' +
      '<h3 style="margin:0;font-size:18px;font-weight:700;">' + escapeHtml(p.title) + '</h3>' +
      '<button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>';
    h += '<div style="font-size:12px;color:#8E8E93;margin-bottom:12px;display:flex;gap:8px;align-items:center;">' +
      '<span style="padding:2px 10px;background:var(--primary-light);border-radius:10px;color:var(--primary);font-weight:600;">' + escapeHtml(p.class_name) + '</span>' +
      '<span style="padding:2px 10px;background:var(--gray-1);border-radius:10px;color:var(--gray-5);">' + escapeHtml(p.team_name) + '</span></div>';
    h += '<div style="font-size:14px;margin-bottom:12px;white-space:pre-wrap;line-height:1.7;color:var(--text-secondary);">' + escapeHtml(p.content || '') + '</div>';
    h += imgHtml;
    h += memHtml;
    if (p.ai_analysis) { h += '<div class="practice-analysis" style="margin-top:12px;"><strong>📊 参考分析</strong><br>' + escapeHtml(p.ai_analysis) + '</div>'; }
    if (p.ai_summary) { h += '<div class="practice-analysis" style="margin-top:8px;"><strong>💡 参考摘要</strong><br>' + escapeHtml(p.ai_summary) + '</div>'; }
    h += '<div style="font-size:12px;color:#888;margin-top:12px;">📅 ' + formatDate(p.created_at) + '</div>';
    m.innerHTML = h;
  } catch (e) {
    showToast('加载失败: ' + e.message);
  }
}
async function reanalyzePractice(practiceId) {
  var btn = document.getElementById('reanalyze-btn-' + practiceId);
  var originalText = '';
  if (btn) { originalText = btn.textContent; btn.textContent = '分析中...'; btn.disabled = true; }
  try {
    var r = await practiceApi.reanalyze(practiceId);
    showToast('参考分析已生成');
    // Refresh the modal by re-fetching practice detail
    var p = await practiceApi.get(practiceId);
    document.querySelector('.modal-overlay').remove();
    showPracticeDetail(practiceId);
  } catch (e) {
    showToast('分析失败: ' + e.message);
    if (btn) { btn.textContent = originalText; btn.disabled = false; }
  }
}

async function showEditPracticeModal(practiceId) {
  try {
    var p = await practiceApi.get(practiceId);
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = '<div class="modal-content"><div class="modal-header"><h3>编辑实践记录</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' +
      '<div class="form-group"><label>活动标题</label><input class="input-field" id="edit-practice-title" value="' + escapeHtml(p.title) + '"></div>' +
      '<div class="form-group"><label>活动内容</label><textarea id="edit-practice-content">' + escapeHtml(p.content || '') + '</textarea></div>' +
      '<div class="form-group" id="edit-member-works"><label>成员分工</label></div>' +
      '<button class="btn-primary" onclick="submitEditPractice(' + practiceId + ')">保存</button></div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
    // Load member works
    var members = await teamApi.members(p.team_id);
    var mList = document.getElementById('edit-member-works');
    if (mList) {
      var h = '';
      for (var j = 0; j < members.length; j++) {
        var m = members[j];
        // Find existing work description for this member
        var desc = '';
        for (var k = 0; k < p.member_records.length; k++) {
          if (p.member_records[k].student_id === m.id) { desc = p.member_records[k].work_description; break; }
        }
        h += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">' +
          '<span style="font-size:14px;min-width:48px;">' + escapeHtml(m.name) + '</span>' +
          '<input class="input-field" style="flex:1;margin-bottom:0;height:40px;" value="' + escapeHtml(desc) + '" data-student-id="' + m.id + '"></div>';
      }
      mList.innerHTML = h;
    }
  } catch (e) {
    showToast('加载失败: ' + e.message);
  }
}

async function submitEditPractice(practiceId) {
  var title = document.getElementById('edit-practice-title');
  var content = document.getElementById('edit-practice-content');
  if (!title || !title.value.trim()) { showToast('请输入活动标题'); return; }
  var inputs = document.querySelectorAll('#edit-member-works input');
  var memberWorks = [];
  for (var j = 0; j < inputs.length; j++) {
    var inp = inputs[j];
    if (inp.value.trim()) { memberWorks.push({ student_id: parseInt(inp.dataset.studentId), work_description: inp.value.trim() }); }
  }
  try {
    await practiceApi.update(practiceId, title.value.trim(), content.value.trim(), memberWorks);
    document.querySelector('.modal-overlay').remove();
    showToast('保存成功');
    // Reopen the practice detail with updated data
    showPracticeDetail(practiceId);
  } catch (e) {
    showToast('保存失败: ' + e.message);
  }
}


async function renderHomeTab() {
  currentView = 'home-tab';
  var old = document.getElementById('featured-practices');
  if (old) old.remove();
  var area = getContentArea();
  area.innerHTML = '<div id="home-carousel" class="carousel-wrap"></div><div style="padding:0 16px;"><div style="font-size:18px;font-weight:700;margin-bottom:12px;">全部作品</div><div id="featured-practices" class="practice-grid"><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div></div></div>';
  try {
    var practices = await api('/practices/featured');
    if (practices && practices.length > 1) renderCarousel('home-carousel', practices);
    var grid = document.getElementById('featured-practices');
    if (grid) {
      grid.innerHTML = practices.map(function(p) {
        return '<div class="featured-card fade-in" onclick="showHomePracticeDetail(' + p.id + ')">' +
          (p.images && p.images.length > 0 ? '<div class="featured-card-images">' + p.images.map(function(i) { return '<img src=\"' + imgUrl(i) + '" onclick="showImageLightbox(this.src)" alt="">'; }).join('') + '</div>' : '<div class="featured-card-images"><div class="placeholder-img">\ud83d\udd2c</div></div>') +
          '<div class="featured-card-body">' +
          '<div class="featured-card-title">' + escapeHtml(p.title) + '</div>' +
          '<div class="featured-card-meta">' +
          '<span>\ud83d\udcda ' + escapeHtml(p.class_name) + '</span>' +
          '<span>\ud83d\udc65 ' + escapeHtml(p.team_name) + '</span>' +
          '<span>\ud83d\udc64 ' + p.member_count + '\u4eba</span>' +
          '</div>' +
          '<div class="featured-card-summary">' + escapeHtml(p.content) + '</div>' +
          (p.ai_summary ? '<div class="featured-card-ai">\ud83d\udca1 ' + escapeHtml(p.ai_summary) + '</div>' : '') +
          '<div class="featured-card-footer"><span>' + formatDate(p.created_at) + '</span></div>' +
          '</div></div>';
      }).join('');
    }
  } catch (e) {
    showToast('\u52a0\u8f7d\u5931\u8d25');
  }
}

function renderCarousel(containerId, practices) {
  var container = document.getElementById(containerId);
  if (!container || !practices || practices.length < 2) return;
  var slides = practices.slice(0, 5);
  var current = 0;
  var timer = null;
  var colors = [
    'linear-gradient(135deg,#667eea 0%,#764ba2 100%)',
    'linear-gradient(135deg,#f093fb 0%,#f5576c 100%)',
    'linear-gradient(135deg,#4facfe 0%,#00f2fe 100%)',
    'linear-gradient(135deg,#43e97b 0%,#38f9d7 100%)',
    'linear-gradient(135deg,#fa709a 0%,#fee140 100%)'
  ];
  function goTo(index) {
    current = index;
    var track = container.querySelector('.carousel-track');
    if (track) track.style.transform = 'translateX(-' + (current * 100) + '%)';
    var dots = container.querySelectorAll('.carousel-dot');
    for (var d = 0; d < dots.length; d++) { dots[d].classList.toggle('active', d === current); }
  }
  function next() { goTo((current + 1) % slides.length); }
  function prev() { goTo((current - 1 + slides.length) % slides.length); }
  var html = '<div class="carousel">';
  html += '<div class="carousel-track">';
  for (var i = 0; i < slides.length; i++) {
    var p = slides[i];
    var c = colors[i % colors.length];
    html += '<div class="carousel-slide" style="background:' + c + ';" onclick="showHomePracticeDetail(' + p.id + ')">';
    html += '<div class="meta">' + escapeHtml(p.class_name) + ' / ' + escapeHtml(p.team_name) + '</div>';
    html += '<h3>' + escapeHtml(p.title) + '</h3>';
    html += '<div class="desc">' + escapeHtml((p.content || '').substring(0, 120)) + '</div>';
    if (p.ai_summary) { html += '<div class="ai-tag">' + escapeHtml(p.ai_summary) + '</div>'; }
    html += '</div>';
  }
  html += '</div>';
  html += '<button class="carousel-btn carousel-prev">\u2039</button>';
  html += '<button class="carousel-btn carousel-next">\u203a</button>';
  html += '<div class="carousel-dots">';
  for (var i = 0; i < slides.length; i++) { html += '<button class="carousel-dot' + (i === 0 ? ' active' : '') + '" data-index="' + i + '"></button>'; }
  html += '</div></div>';
  container.innerHTML = html;
  var prevBtn = container.querySelector('.carousel-prev');
  var nextBtn = container.querySelector('.carousel-next');
  if (prevBtn) prevBtn.onclick = function(e) { e.stopPropagation(); prev(); };
  if (nextBtn) nextBtn.onclick = function(e) { e.stopPropagation(); next(); };
  var dots = container.querySelectorAll('.carousel-dot');
  for (var d = 0; d < dots.length; d++) {
    (function(idx) {
      dots[idx].onclick = function(e) { e.stopPropagation(); goTo(parseInt(this.getAttribute('data-index'))); };
    })(d);
  }
  function startTimer() { if (timer) clearInterval(timer); timer = setInterval(next, 4000); }
  startTimer();
  container.onmouseenter = function() { if (timer) clearInterval(timer); };
  container.onmouseleave = startTimer;
}



function showImageLightbox(src) {
  var overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.background = 'rgba(0,0,0,0.88)';
  overlay.innerHTML = '<div style="position:relative;max-width:90vw;max-height:90vh;">' +
    '<img src="' + src + '" style="max-width:100%;max-height:85vh;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,0.4);">' +
    '<button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()" style="position:absolute;top:-44px;right:0;background:rgba(255,255,255,0.15);color:#fff;font-size:18px;padding:6px 14px;">✕</button></div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) overlay.remove();
  });
}

function renderStars(score) {
  if (!score && score !== 0) return '';
  var filled = Math.round(score / 20);
  var html = '';
  for (var i = 1; i <= 5; i++) {
    html += i <= filled ? '<span style="color:#FF9500;font-size:18px;">★</span>' : '<span style="color:#E5E5EA;font-size:18px;">★</span>';
  }
  return html;
}

async function submitEvaluation(practiceId) {
  var scoreInput = document.getElementById('eval-score-' + practiceId);
  var commentInput = document.getElementById('eval-comment-' + practiceId);
  var score = parseInt(scoreInput.value);
  if (isNaN(score) || score < 1 || score > 100) {
    showToast('请输入 1-100 之间的分数');
    return;
  }
  try {
    await practiceApi.evaluate(practiceId, score, commentInput.value.trim());
    showToast('评价已保存');
    document.querySelector('.modal-overlay').remove();
    showPracticeDetail(practiceId);
  } catch (e) {
    showToast('评价失败: ' + e.message);
  }
}

function setStarRating(practiceId, stars) {
  var score = stars * 20;
  var input = document.getElementById('eval-score-' + practiceId);
  if (input) input.value = score;
  var starsContainer = document.getElementById('eval-stars-' + practiceId);
  if (starsContainer) {
    var html = '';
    for (var i = 1; i <= 5; i++) {
      html += '<span onclick="setStarRating(' + practiceId + ',' + i + ')" style="cursor:pointer;font-size:24px;' + (i <= stars ? 'color:#FF9500;' : 'color:#E5E5EA;') + '">★</span>';
    }
    html += ' <span style="font-size:14px;color:#636366;">' + score + '分</span>';
    starsContainer.innerHTML = html;
  }
}


async function renderTeamPublicPage(teamId) {
  var tabBar = document.getElementById('tab-bar');
  if (tabBar) tabBar.style.display = 'none';
  showPage('main-page');
  var area = getContentArea();
  area.style.paddingBottom = '16px';
  area.innerHTML = '<div style="text-align:center;padding:32px;color:#8E8E93;font-size:14px;">加载中...</div>';
  try {
    var data = await api('/teams/public/' + teamId);
    var student = getStudentInfo();
    var h = '';
    // ── Team Header ──
    h += '<div style="background:var(--white);padding:16px;border-bottom:0.5px solid var(--gray-2);position:sticky;top:0;z-index:10;backdrop-filter:blur(20px);">';
    h += '<div style="font-size:12px;color:#8E8E93;margin-bottom:4px;">' + escapeHtml(data.team.class_name) + '</div>';
    h += '<div style="display:flex;align-items:center;justify-content:space-between;">';
    h += '<div style="font-size:20px;font-weight:700;">' + escapeHtml(data.team.name) + '</div>';
    h += '<button onclick="shareTeamUrl(' + teamId + ')" style="padding:8px 20px;border-radius:20px;border:none;background:var(--primary-gradient);color:#fff;font-size:14px;font-weight:600;cursor:pointer;box-shadow:0 2px 10px rgba(79,110,247,0.2);">分享</button></div></div>';

    h += '<div style="padding:16px;">';
    // ── Members ──
    h += '<div style="font-size:17px;font-weight:700;margin-bottom:10px;">成员 (' + data.members.length + ')</div>';
    h += '<div style="background:#fff;border-radius:14px;padding:8px 16px;box-shadow:var(--shadow-card);margin-bottom:16px;border:0.5px solid rgba(0,0,0,0.03);">';
    for (var i = 0; i < data.members.length; i++) {
      var m = data.members[i];
      h += '<div style="display:flex;align-items:center;padding:10px 0;border-bottom:' + (i < data.members.length - 1 ? '0.5px solid #e5e5ea' : 'none') + ';">';
      h += '<div style="width:40px;height:40px;border-radius:50%;background:var(--primary-gradient);display:flex;align-items:center;justify-content:center;margin-right:12px;font-size:16px;color:#fff;font-weight:600;box-shadow:0 2px 8px rgba(79,110,247,0.2);">' + escapeHtml(m.name.charAt(0)) + '</div>';
      h += '<div><div style="font-size:15px;font-weight:600;">' + escapeHtml(m.name) + '</div><div style="font-size:12px;color:#8E8E93;">' + escapeHtml(m.role || '') + '</div></div></div>';
    }
    h += '</div>';

    // ── Student Login or Info ──
    if (student) {
      h += '<div style="background:var(--success-light);border-radius:14px;padding:14px 16px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;border:0.5px solid rgba(52,199,89,0.15);">';
      h += '<div style="display:flex;align-items:center;gap:8px;"><span style="width:36px;height:36px;border-radius:50%;background:var(--success);display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;">👤</span><div><div style="font-size:14px;font-weight:600;">' + escapeHtml(student.name) + '</div><div style="font-size:12px;color:var(--success);">已登录</div></div></div>';
      h += '<button onclick="localStorage.removeItem(\'studentToken\');localStorage.removeItem(\'studentInfo\');renderTeamPublicPage(' + teamId + ')" style="padding:6px 16px;border-radius:16px;border:none;background:#fff;color:var(--gray-5);font-size:12px;cursor:pointer;box-shadow:var(--shadow-sm);">退出</button></div>';
    } else {
      h += '<div style="background:#fff;border-radius:14px;padding:16px;margin-bottom:16px;box-shadow:var(--shadow-card);border:0.5px solid rgba(0,0,0,0.03);">';
      h += '<div style="font-size:14px;font-weight:700;margin-bottom:10px;">🔑 学生登录</div>';
      h += '<div style="display:flex;gap:8px;">';
      h += '<input id="student-login-name" class="input-field" placeholder="输入你的姓名" style="flex:1;margin-bottom:0;height:42px;">';
      h += '<input id="student-login-pin" type="password" class="input-field" placeholder="个人口令" style="flex:1;margin-bottom:0;height:42px;">';
      h += '<button class="btn-primary" style="width:auto;padding:0 24px;height:42px;font-size:14px;" onclick="studentLogin(' + teamId + ')">登录</button></div></div>';
    }

    // ── Practices ──
    h += '<div style="font-size:17px;font-weight:700;margin-bottom:10px;">实践记录 (' + data.practices.length + ')</div>';
    if (data.practices.length === 0) {
      h += '<div class="empty-state"><div class="icon">📝</div><p>暂无实践记录</p></div>';
    } else {
      for (var i = 0; i < data.practices.length; i++) {
        var p = data.practices[i];
        h += '<div style="background:#fff;border-radius:14px;padding:16px;margin-bottom:12px;box-shadow:var(--shadow-card);border:0.5px solid rgba(0,0,0,0.03);">';
        h += '<div style="font-size:16px;font-weight:700;margin-bottom:4px;">' + escapeHtml(p.title) + '</div>';
        h += '<div style="font-size:12px;color:#8E8E93;margin-bottom:8px;">📅 ' + (p.created_at ? p.created_at.substring(0,10) : '') + '</div>';
        if (p.content) h += '<div style="font-size:14px;color:#636366;margin-bottom:8px;line-height:1.6;">' + escapeHtml(p.content.substring(0,200)) + '</div>';
        if (p.member_records && p.member_records.length > 0) {
          h += '<div style="font-size:12px;color:#636366;padding:10px 12px;background:var(--gray-1);border-radius:10px;margin-bottom:8px;">';
          for (var j = 0; j < p.member_records.length; j++) {
            var r = p.member_records[j];
            h += '<div style="padding:3px 0;"><b style="color:var(--text);">' + escapeHtml(r.student_name || '') + '</b>: ' + escapeHtml(r.work_description || '') + '</div>';
          }
          h += '</div>';
        }
        if (p.ai_summary) h += '<div class="practice-analysis">💡 ' + escapeHtml(p.ai_summary) + '</div>';
        // ── Evaluation section for logged-in students ──
        if (student) {
          h += '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">';
          h += '<button class="btn-secondary" style="font-size:12px;padding:4px 12px;" onclick="showStudentEvalModal(' + p.id + ',' + teamId + ',\'self\')">📝 自评</button>';
          h += '<button class="btn-secondary" style="font-size:12px;padding:4px 12px;" onclick="showStudentEvalModal(' + p.id + ',' + teamId + ',\'peer\')">👥 互评</button>';
          h += '<button class="btn-secondary" style="font-size:12px;padding:4px 12px;" onclick="showStudentEvalModal(' + p.id + ',' + teamId + ',\'teacher\')">👨‍🏫 评老师</button>';
          h += '</div>';
          // Show evaluation summary
          h += '<div id="eval-summary-' + p.id + '" style="margin-top:6px;"></div>';
        }
        h += '</div>';
      }
    }
    h += '</div>';
    area.innerHTML = h;

    // Load evaluations if student logged in
    if (student) {
      for (var i = 0; i < data.practices.length; i++) {
        loadEvalSummary(data.practices[i].id, student.student_id);
      }
    }
  } catch (e) {
    getContentArea().innerHTML = '<div style="text-align:center;padding:32px;color:#8E8E93;font-size:14px;">加载失败: ' + e.message + '</div>';
  }
}

function shareTeamUrl(teamId) {
  var url = window.location.origin + '/team/' + teamId;
  if (navigator.share) {
    navigator.share({ title: '综合实践 - 小组', url: url }).catch(function() {});
  } else {
    navigator.clipboard.writeText(url).then(function() {
      showToast('链接已复制到剪贴板');
    }).catch(function() {
      showToast(url);
    });
  }
}

async function studentLogin(teamId) {
  var nameInput = document.getElementById('student-login-name');
  var name = nameInput.value.trim();
  if (!name) { showToast('请输入姓名'); return; }
  try {
    var res = await studentApi.login(teamId, name, $('student-login-pin').value);
    setStudentInfo(res.access_token, { student_id: res.student_id, name: res.name, team_id: res.team_id });
    showToast('登录成功');
    renderTeamPublicPage(teamId);
  } catch (e) {
    showToast('登录失败: ' + e.message);
  }
}

async function showStudentEvalModal(practiceId, teamId, mode) {
  var data = await api('/teams/public/' + teamId);
  var student = getStudentInfo();
  if (!student) { showToast('请先登录'); return; }
  var members = data.members;
  var titleMap = { self: '自评', peer: '互评', teacher: '评老师' };
  var title = titleMap[mode] || '评价';

  var overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  var html = '<div class="modal-content" style="max-width:400px;"><div class="modal-header"><h3>' + title + '</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>';

  html += '<div id="eval-form-inner-' + practiceId + '">';

  if (mode === 'self') {
    html += '<div style="font-size:14px;color:#636366;margin-bottom:8px;">对自己在这项实践中的表现进行评价</div>';
    html += renderStarSelector('eval-self-' + practiceId, practiceId);
    html += '<textarea id="eval-self-comment-' + practiceId + '" class="input-field" placeholder="评语（选填）" style="height:60px;resize:none;margin-bottom:8px;"></textarea>';
    html += '<button class="btn-primary" style="height:40px;font-size:14px;" onclick="submitStudentEval(' + practiceId + ',\'self\',' + student.student_id + ')">提交评价</button>';
  } else if (mode === 'peer') {
    html += '<div style="font-size:14px;color:#636366;margin-bottom:8px;">选择要评价的同学</div>';
    for (var i = 0; i < members.length; i++) {
      var m = members[i];
      if (m.id === student.student_id) continue;
      html += '<div style="background:#f5f5f7;border-radius:8px;padding:10px 12px;margin-bottom:8px;">';
      html += '<div style="font-size:14px;font-weight:500;margin-bottom:4px;">' + escapeHtml(m.name) + '</div>';
      html += renderStarSelector('eval-peer-' + practiceId + '-' + m.id, practiceId);
      html += '<textarea id="eval-peer-comment-' + practiceId + '-' + m.id + '" class="input-field" placeholder="评语（选填）" style="height:50px;resize:none;margin-bottom:4px;"></textarea>';
      html += '<button class="btn-primary" style="height:34px;font-size:13px;" onclick="submitStudentEval(' + practiceId + ',\'peer\',' + m.id + ')">提交对 ' + escapeHtml(m.name) + ' 的评价</button>';
      html += '</div>';
    }
  } else if (mode === 'teacher') {
    html += '<div style="font-size:14px;color:#636366;margin-bottom:8px;">对指导老师进行评价</div>';
    html += renderStarSelector('eval-teacher-' + practiceId, practiceId);
    html += '<textarea id="eval-teacher-comment-' + practiceId + '" class="input-field" placeholder="评语（选填）" style="height:60px;resize:none;margin-bottom:8px;"></textarea>';
    html += '<button class="btn-primary" style="height:40px;font-size:14px;" onclick="submitStudentEval(' + practiceId + ',\'teacher\',0)">提交评价</button>';
  }

  html += '</div></div>';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
}

function renderStarSelector(containerId, practiceId) {
  var html = '<div id="' + containerId + '" style="margin-bottom:6px;">';
  for (var s = 1; s <= 5; s++) {
    html += '<span onclick="selectEvalStar(\'' + containerId + '\',' + s + ')" style="cursor:pointer;font-size:28px;color:#E5E5EA;transition:color 0.1s;" data-val="' + s + '">★</span>';
  }
  html += ' <span style="font-size:13px;color:#636366;">点击星星评分</span>';
  html += '<input type="hidden" id="' + containerId + '-score" value="0"></div>';
  return html;
}

function selectEvalStar(containerId, stars) {
  var score = stars * 20;
  document.getElementById(containerId + '-score').value = score;
  var spans = document.querySelectorAll('#' + containerId + ' span[data-val]');
  for (var i = 0; i < spans.length; i++) {
    var s = parseInt(spans[i].getAttribute('data-val'));
    spans[i].style.color = s <= stars ? '#FF9500' : '#E5E5EA';
  }
  var label = containerId + ' span:last-child';
  var labelEl = document.querySelector('#' + containerId);
}

async function submitStudentEval(practiceId, targetType, targetId) {
  var student = getStudentInfo();
  if (!student) { showToast('请先登录'); return; }
  var prefix = 'eval-' + targetType + '-' + practiceId;
  var containerId = prefix;
  if (targetType === 'peer') containerId = prefix + '-' + targetId;
  var scoreEl = document.getElementById(containerId + '-score');
  var score = parseInt(scoreEl ? scoreEl.value : '0');
  if (!score || score < 20) { showToast('请先点击星星评分'); return; }
  var commentEl = document.getElementById(containerId + '-comment-' + practiceId);
  if (targetType === 'peer') commentEl = document.getElementById(prefix + '-comment-' + practiceId + '-' + targetId);
  var comment = commentEl ? commentEl.value.trim() : '';
  try {
    await practiceApi.createEvaluation(practiceId, targetType, targetId, score, comment);
    showToast('评价已提交');
    document.querySelector('.modal-overlay').remove();
    // Refresh evaluation summary
    loadEvalSummary(practiceId, student.student_id);
  } catch (e) {
    showToast('提交失败: ' + e.message);
  }
}

async function loadEvalSummary(practiceId, myStudentId) {
  var container = document.getElementById('eval-summary-' + practiceId);
  if (!container) return;
  try {
    var evals = await practiceApi.listEvaluations(practiceId);
    if (evals.length === 0) { container.innerHTML = ''; return; }
    // Group by type
    var selfEvals = evals.filter(function(e) { return e.evaluator_id === myStudentId && e.target_type === 'self'; });
    var peerEvals = evals.filter(function(e) { return e.target_type === 'peer'; });
    var teacherEvals = evals.filter(function(e) { return e.target_type === 'teacher'; });
    var practiceEvals = evals.filter(function(e) { return e.target_type === 'practice'; });
    var myPeerEvals = evals.filter(function(e) { return e.evaluator_id === myStudentId && e.target_type === 'peer'; });
    // Show summary
    var h = '<div style="font-size:12px;color:#636366;padding:10px 12px;background:var(--warning-light);border-radius:10px;margin-top:6px;line-height:1.8;">';
    if (peerEvals.length > 0) {
      var avg = Math.round(peerEvals.reduce(function(s, e) { return s + e.score; }, 0) / peerEvals.length);
      h += '<span>互评平均分: <b>' + avg + '</b> (' + peerEvals.length + '人评) </span>';
    }
    if (selfEvals.length > 0) h += '<span>你的自评: <b>' + selfEvals[0].score + '</b>分 </span>';
    if (myPeerEvals.length > 0) h += '<span>你已评 ' + myPeerEvals.length + ' 位同学 </span>';
    if (practiceEvals.length > 0) h += '<span>老师评分: <b>' + practiceEvals[0].score + '</b>分 </span>';
    if (teacherEvals.length > 0) {
      var avgT = Math.round(teacherEvals.reduce(function(s, e) { return s + e.score; }, 0) / teacherEvals.length);
      h += '<span>学生评老师: <b>' + avgT + '</b>分</span>';
    }
    h += '</div>';
    // Detailed list
    if (peerEvals.length > 0) {
      h += '<div style="font-size:11px;color:#8E8E93;margin-top:4px;">';
      for (var i = 0; i < peerEvals.length; i++) {
        var e = peerEvals[i];
        h += '<div>' + escapeHtml(e.evaluator_name) + ' → ' + escapeHtml(e.target_name) + ': ' + e.score + '分' + (e.comment ? ' "' + escapeHtml(e.comment) + '"' : '') + '</div>';
      }
      h += '</div>';
    }
    container.innerHTML = h;
  } catch (e) {
    // silently fail
  }
}

init();
