let adminTeachers = [];
let adminClasses = [];
let adminTab = 'teachers';
let adminClassId = null;
let adminStudentOffset = 0;
let adminStudentQuery = '';
let adminStudentPage = { total: 0, items: [] };
let adminSearchTimer = null;

function adminAttr(value) {
  return escapeHtml(String(value == null ? '' : value)).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function adminError(error) {
  showToast(error.message || '操作失败', 4000);
}

async function loadAdminDashboard() {
  try {
    const [stats, teachers, classes] = await Promise.all([
      adminApi.overview(), adminApi.teachers(), adminApi.classes()
    ]);
    adminTeachers = teachers;
    adminClasses = classes;
    $('admin-stats').innerHTML = [
      ['教师', stats.teachers], ['班级', stats.classes], ['小组', stats.teams],
      ['学生', stats.students], ['实践作品', stats.practices]
    ].map(function(item) {
      return '<div class="admin-stat"><strong>' + item[1] + '</strong><span>' + item[0] + '</span></div>';
    }).join('');
    if (!adminClasses.some(c => c.id === adminClassId)) {
      adminClassId = adminClasses.length ? adminClasses[0].id : null;
    }
    setAdminTab(adminTab);
  } catch (error) { adminError(error); }
}

function setAdminTab(tab) {
  adminTab = tab;
  ['teachers', 'classes', 'students'].forEach(function(name) {
    $('admin-tab-' + name).classList.toggle('active', name === tab);
  });
  if (tab === 'teachers') renderAdminTeachers();
  else if (tab === 'classes') renderAdminClasses();
  else renderAdminStudentsShell();
}

function filterAdminRows(kind, value) {
  const query = value.trim().toLocaleLowerCase();
  document.querySelectorAll('.admin-row[data-kind="' + kind + '"]').forEach(function(row) {
    row.classList.toggle('hidden', !row.dataset.search.toLocaleLowerCase().includes(query));
  });
}

function renderAdminTeachers() {
  $('admin-content').innerHTML =
    '<div class="admin-section-head"><h2>教师账号</h2><button class="btn-primary" onclick="openAdminTeacherForm()">+ 新增教师</button></div>' +
    '<input class="input-field admin-search" placeholder="搜索教师或学校" oninput="filterAdminRows(\'teacher\',this.value)">' +
    (adminTeachers.length ? adminTeachers.map(function(teacher) {
      return '<div class="admin-row" data-kind="teacher" data-search="' + adminAttr(teacher.name + ' ' + teacher.school) + '">' +
        '<div class="admin-row-main"><strong>' + escapeHtml(teacher.name) + '</strong>' +
        '<span class="admin-status ' + (teacher.authorized ? 'enabled' : 'disabled') + '">' +
        (teacher.authorized ? '已启用' : '已停用') + '</span></div>' +
        '<div class="admin-row-sub">' + escapeHtml(teacher.school || '未填写学校') + ' · ' + teacher.class_count + ' 个班级</div>' +
        '<div class="admin-actions"><button onclick="openAdminTeacherForm(' + teacher.id + ')">编辑</button>' +
        '<button onclick="openAdminTeacherPassword(' + teacher.id + ')">重置密码</button>' +
        '<button onclick="toggleAdminTeacher(' + teacher.id + ')">' + (teacher.authorized ? '停用' : '启用') + '</button></div></div>';
    }).join('') : '<div class="admin-empty">暂无教师账号</div>');
}

function adminModal(title, body) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal-content"><div class="modal-header"><h3>' + escapeHtml(title) +
    '</h3><button class="modal-close" onclick="this.closest(\'.modal-overlay\').remove()">✕</button></div>' + body + '</div>';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', function(event) { if (event.target === overlay) overlay.remove(); });
  return overlay;
}

function closeAdminModal() {
  const modal = document.querySelector('.modal-overlay');
  if (modal) modal.remove();
}

function openAdminTeacherForm(id) {
  const teacher = adminTeachers.find(item => item.id === id);
  adminModal(teacher ? '编辑教师' : '新增教师',
    '<label>教师姓名</label><input id="admin-edit-name" class="input-field" maxlength="64" value="' + adminAttr(teacher ? teacher.name : '') + '">' +
    '<label>学校</label><input id="admin-edit-school" class="input-field" maxlength="128" value="' + adminAttr(teacher ? teacher.school : '') + '">' +
    (teacher ? '' : '<label>初始密码（至少12位）</label><input id="admin-edit-password" class="input-field" type="password" autocomplete="new-password">' +
      '<label>确认密码</label><input id="admin-edit-confirm" class="input-field" type="password" autocomplete="new-password">') +
    '<button class="btn-primary" onclick="saveAdminTeacher(' + (teacher ? teacher.id : 'null') + ')">保存</button>'
  );
}

async function saveAdminTeacher(id) {
  const name = $('admin-edit-name').value.trim();
  const school = $('admin-edit-school').value.trim();
  if (!name) { showToast('请输入教师姓名'); return; }
  try {
    if (id) {
      const teacher = adminTeachers.find(item => item.id === id);
      await adminApi.updateTeacher(id, { name, school, authorized: teacher.authorized });
    } else {
      const password = $('admin-edit-password').value;
      if (password.length < 12 || password !== $('admin-edit-confirm').value) {
        showToast('密码至少12位且两次输入一致'); return;
      }
      await adminApi.addTeacher(name, school, password);
    }
    closeAdminModal();
    showToast('教师账号已保存');
    await loadAdminDashboard();
  } catch (error) { adminError(error); }
}

function openAdminTeacherPassword(id) {
  const teacher = adminTeachers.find(item => item.id === id);
  if (!teacher) return;
  adminModal('重置 ' + teacher.name + ' 的密码',
    '<p class="admin-note">保存后，该教师现有登录凭证将失效。</p>' +
    '<label>新密码（至少12位）</label><input id="admin-reset-password" class="input-field" type="password" autocomplete="new-password">' +
    '<label>确认新密码</label><input id="admin-reset-confirm" class="input-field" type="password" autocomplete="new-password">' +
    '<button class="btn-primary" onclick="saveAdminTeacherPassword(' + id + ')">重置密码</button>'
  );
}

async function saveAdminTeacherPassword(id) {
  const password = $('admin-reset-password').value;
  if (password.length < 12 || password !== $('admin-reset-confirm').value) {
    showToast('密码至少12位且两次输入一致'); return;
  }
  try {
    await adminApi.resetTeacherPassword(id, password);
    closeAdminModal();
    showToast('教师密码已重置');
  } catch (error) { adminError(error); }
}

async function toggleAdminTeacher(id) {
  const teacher = adminTeachers.find(item => item.id === id);
  if (!teacher) return;
  if (teacher.authorized && !confirm('停用后，该教师会立即无法访问其班级和未公开作品。确定停用吗？')) return;
  try {
    await adminApi.updateTeacher(id, {
      name: teacher.name, school: teacher.school, authorized: !teacher.authorized
    });
    showToast(teacher.authorized ? '教师已停用' : '教师已启用');
    await loadAdminDashboard();
  } catch (error) { adminError(error); }
}

function renderAdminClasses() {
  $('admin-content').innerHTML =
    '<div class="admin-section-head"><h2>全校班级</h2><button class="btn-primary" onclick="openAdminClassForm()">+ 新增班级</button></div>' +
    '<input class="input-field admin-search" placeholder="搜索班级或教师" oninput="filterAdminRows(\'class\',this.value)">' +
    (adminClasses.length ? adminClasses.map(function(item) {
      return '<div class="admin-row" data-kind="class" data-search="' + adminAttr(item.name + ' ' + item.teacher_name) + '">' +
        '<div class="admin-row-main"><strong>' + escapeHtml(item.name) + '</strong></div>' +
        '<div class="admin-row-sub">' + escapeHtml(item.teacher_name) + ' · ' + escapeHtml(item.grade || '未设置年级') +
        ' · ' + item.team_count + ' 个小组 · ' + item.student_count + ' 名学生</div>' +
        '<div class="admin-actions"><button onclick="adminViewStudents(' + item.id + ')">管理学生</button>' +
        '<button onclick="openAdminClassForm(' + item.id + ')">编辑</button>' +
        '<button onclick="deleteAdminClass(' + item.id + ')">删除空班级</button></div></div>';
    }).join('') : '<div class="admin-empty">暂无班级</div>');
}

function openAdminClassForm(id) {
  const item = adminClasses.find(value => value.id === id);
  const options = adminTeachers.map(function(teacher) {
    return '<option value="' + teacher.id + '" ' + (item && item.teacher_id === teacher.id ? 'selected' : '') + '>' +
      escapeHtml(teacher.name) + (teacher.authorized ? '' : '（已停用）') + '</option>';
  }).join('');
  adminModal(item ? '编辑班级' : '新增班级',
    '<label>所属教师</label><select id="admin-class-teacher" class="input-field">' + options + '</select>' +
    '<label>班级名称</label><input id="admin-class-name" class="input-field" maxlength="128" value="' + adminAttr(item ? item.name : '') + '">' +
    '<label>年级</label><input id="admin-class-grade" class="input-field" maxlength="32" value="' + adminAttr(item ? item.grade : '') + '">' +
    '<label>说明</label><textarea id="admin-class-description" class="input-field admin-textarea">' + escapeHtml(item ? item.description : '') + '</textarea>' +
    '<button class="btn-primary" onclick="saveAdminClass(' + (item ? item.id : 'null') + ')">保存</button>'
  );
}

async function saveAdminClass(id) {
  const teacherId = Number($('admin-class-teacher').value);
  const name = $('admin-class-name').value.trim();
  if (!teacherId || !name) { showToast('请选择教师并填写班级名称'); return; }
  const oldClass = adminClasses.find(item => item.id === id);
  if (oldClass && oldClass.teacher_id !== teacherId &&
      !confirm('变更所属教师后，班级、小组、学生和实践作品将交由新教师管理。确定吗？')) return;
  const data = {
    teacher_id: teacherId, name, grade: $('admin-class-grade').value.trim(),
    description: $('admin-class-description').value.trim()
  };
  try {
    if (id) await adminApi.updateClass(id, data);
    else await adminApi.addClass(data);
    closeAdminModal();
    showToast('班级已保存');
    await loadAdminDashboard();
  } catch (error) { adminError(error); }
}

async function deleteAdminClass(id) {
  const item = adminClasses.find(value => value.id === id);
  if (!item || !confirm('仅能删除没有小组和学生的班级。确定删除“' + item.name + '”吗？')) return;
  try {
    await adminApi.deleteClass(id);
    showToast('空班级已删除');
    await loadAdminDashboard();
  } catch (error) { adminError(error); }
}

function adminViewStudents(classId) {
  adminClassId = classId;
  adminStudentOffset = 0;
  adminStudentQuery = '';
  setAdminTab('students');
}

function renderAdminStudentsShell() {
  const classOptions = adminClasses.map(function(item) {
    return '<option value="' + item.id + '" ' + (item.id === adminClassId ? 'selected' : '') + '>' +
      escapeHtml(item.name + ' · ' + item.teacher_name) + '</option>';
  }).join('');
  $('admin-content').innerHTML =
    '<div class="admin-section-head"><h2>学生管理</h2><button class="btn-primary" ' +
    (adminClassId ? 'onclick="openAdminStudentForm()"' : 'disabled') + '>+ 新增学生</button></div>' +
    (adminClasses.length ? '<div class="admin-student-filters"><select class="input-field" onchange="adminSelectClass(this.value)">' +
      classOptions + '</select><input id="admin-student-search" class="input-field" placeholder="搜索姓名或学号" value="' +
      adminAttr(adminStudentQuery) + '" oninput="adminSearchStudents(this.value)"></div>' : '') +
    '<div id="admin-student-list">' + (adminClasses.length ? '加载中...' : '<div class="admin-empty">请先创建班级</div>') + '</div>';
  if (adminClassId) loadAdminStudents();
}

function adminSelectClass(value) {
  adminClassId = Number(value);
  adminStudentOffset = 0;
  adminStudentQuery = '';
  renderAdminStudentsShell();
}

function adminSearchStudents(value) {
  adminStudentQuery = value;
  adminStudentOffset = 0;
  clearTimeout(adminSearchTimer);
  adminSearchTimer = setTimeout(loadAdminStudents, 250);
}

async function loadAdminStudents() {
  if (!adminClassId) return;
  const requestedClass = adminClassId;
  const requestedQuery = adminStudentQuery;
  const requestedOffset = adminStudentOffset;
  try {
    const page = await adminApi.students(requestedClass, requestedQuery, requestedOffset);
    if (adminClassId !== requestedClass || adminStudentQuery !== requestedQuery || adminStudentOffset !== requestedOffset) return;
    adminStudentPage = page;
    const list = $('admin-student-list');
    if (!list) return;
    list.innerHTML = page.items.length ? page.items.map(function(student) {
      return '<div class="admin-row"><div class="admin-row-main"><strong>' + escapeHtml(student.name) + '</strong></div>' +
      '<div class="admin-row-sub">学号：' + escapeHtml(student.student_no || '未填写') +
        ' · 手机号：' + escapeHtml(student.phone || '未填写') +
        ' · 小组：' + escapeHtml(student.team_name || '未分组') +
        ' · 职责：' + escapeHtml(student.role || '未设置') + '</div>' +
        '<div class="admin-actions"><button onclick="openAdminStudentForm(' + student.id + ')">编辑</button>' +
        '<button onclick="resetAdminStudentCode(' + student.id + ')">重置密码</button>' +
        '<button onclick="deleteAdminStudent(' + student.id + ')">删除</button></div></div>';
    }).join('') : '<div class="admin-empty">没有符合条件的学生</div>';
    list.innerHTML += '<div class="admin-pager"><span>共 ' + page.total + ' 名学生</span>' +
      '<div><button ' + (requestedOffset === 0 ? 'disabled' : '') + ' onclick="adminStudentPageChange(-100)">上一页</button>' +
      '<button ' + (requestedOffset + page.items.length >= page.total ? 'disabled' : '') +
      ' onclick="adminStudentPageChange(100)">下一页</button></div></div>';
  } catch (error) { adminError(error); }
}

function adminStudentPageChange(delta) {
  adminStudentOffset = Math.max(0, adminStudentOffset + delta);
  loadAdminStudents();
}

async function openAdminStudentForm(id) {
  const student = adminStudentPage.items.find(item => item.id === id);
  const classId = student ? student.class_id : adminClassId;
  if (!classId) return;
  try {
    const teams = await adminApi.classTeams(classId);
    const options = '<option value="">未分组</option>' + teams.map(function(team) {
      return '<option value="' + team.id + '" ' + (student && student.team_id === team.id ? 'selected' : '') + '>' +
        escapeHtml(team.name) + '</option>';
    }).join('');
    adminModal(student ? '编辑学生' : '新增学生',
      '<label>姓名</label><input id="admin-student-name" class="input-field" maxlength="64" value="' + adminAttr(student ? student.name : '') + '">' +
      '<label>学号</label><input id="admin-student-no" class="input-field" maxlength="32" value="' + adminAttr(student ? student.student_no : '') + '">' +
      '<label>手机号</label><input id="admin-student-phone" class="input-field" maxlength="20" inputmode="tel" value="' + adminAttr(student ? student.phone : '') + '">' +
      '<label>年级</label><input id="admin-student-grade" class="input-field" maxlength="32" value="' + adminAttr(student ? student.grade : '') + '">' +
      '<label>出生日期</label><input id="admin-student-birth" class="input-field" type="date" value="' + adminAttr(student ? student.birth_date : '') + '">' +
      '<label>小组</label><select id="admin-student-team" class="input-field">' + options + '</select>' +
      '<label>职责</label><input id="admin-student-role" class="input-field" maxlength="64" value="' + adminAttr(student ? student.role : '') + '">' +
      '<button class="btn-primary" onclick="saveAdminStudent(' + (student ? student.id : 'null') + ',' + classId + ')">保存</button>'
    );
  } catch (error) { adminError(error); }
}

async function saveAdminStudent(id, classId) {
  const name = $('admin-student-name').value.trim();
  if (!name) { showToast('请输入学生姓名'); return; }
  const data = {
    class_id: classId,
    name,
    student_no: $('admin-student-no').value.trim(),
    phone: $('admin-student-phone').value.trim(),
    grade: $('admin-student-grade').value.trim(),
    birth_date: $('admin-student-birth').value || null,
    team_id: $('admin-student-team').value ? Number($('admin-student-team').value) : null,
    role: $('admin-student-role').value.trim()
  };
  try {
    if (id) await adminApi.updateStudent(id, data);
    else await adminApi.addStudent(data);
    closeAdminModal();
    showToast('学生资料已保存');
    await loadAdminDashboard();
  } catch (error) { adminError(error); }
}

async function resetAdminStudentCode(id) {
  const student = adminStudentPage.items.find(item => item.id === id);
  if (!student || !confirm('重置后密码将是登记手机号后6位，旧密码会失效。确定重置“' + student.name + '”的密码吗？')) return;
  try {
    await adminApi.resetStudentCode(id);
    adminModal('学生登录密码', '<p class="admin-note">已重置为登记手机号后6位。' + escapeHtml(student.name) + ' 登录后必须先修改密码。</p>' +
      '<button class="btn-primary" onclick="closeAdminModal()">完成</button>');
  } catch (error) { adminError(error); }
}

async function deleteAdminStudent(id) {
  const student = adminStudentPage.items.find(item => item.id === id);
  if (!student || !confirm('仅能删除没有实践和评价记录的学生。确定删除“' + student.name + '”吗？')) return;
  try {
    await adminApi.deleteStudent(id);
    showToast('学生已删除');
    await loadAdminDashboard();
  } catch (error) { adminError(error); }
}
