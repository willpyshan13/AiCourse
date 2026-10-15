const API_BASE = '/api';

let authToken = localStorage.getItem('token') || '';

function setToken(token) {
  authToken = token;
  localStorage.setItem('token', token);
}

function clearToken() {
  fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => {});
  authToken = '';
  localStorage.removeItem('studentToken');
  localStorage.removeItem('studentInfo');
  localStorage.removeItem('token');
}

function getToken() {
  return authToken;
}

function getStudentToken() {
  return localStorage.getItem('studentToken') || '';
}

function getStudentInfo() {
  try {
    return JSON.parse(localStorage.getItem('studentInfo') || 'null');
  } catch { return null; }
}

function setStudentInfo(token, info) {
  localStorage.setItem('studentToken', token);
  localStorage.setItem('studentInfo', JSON.stringify(info));
}

async function api(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = { ...options.headers };
  const studentToken = getStudentToken();
  const studentEvaluation = /^\/practices\/\d+\/evaluations$/.test(path) && options.method === 'POST';
  const token = studentEvaluation ? studentToken : authToken;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    window.location.reload();
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

async function studentRequest(path, options = {}) {
  const headers = { ...options.headers };
  const token = getStudentToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('studentToken');
      localStorage.removeItem('studentInfo');
    }
    const error = await response.json().catch(() => ({ detail: '操作失败' }));
    throw new Error(error.detail || '操作失败');
  }
  return response.json();
}

const authApi = {
  login: (name, password) =>
    api('/auth/login', { method: 'POST', body: { name, password } }),
  me: () => api('/auth/me'),
};

let adminToken = '';
async function adminRequest(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (adminToken) headers.Authorization = `Bearer ${adminToken}`;
  const res = await fetch(`/api/admin${path}`, { ...options, headers,
    body: options.body ? JSON.stringify(options.body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || '操作失败');
  return data;
}

const adminApi = {
  login: (username, password) => adminRequest('/login', { method: 'POST', body: { username, password } }),
  overview: () => adminRequest('/overview'),
  teachers: () => adminRequest('/teachers'),
  addTeacher: (name, school, password) => adminRequest('/teachers', { method: 'POST', body: { name, school, password } }),
  updateTeacher: (id, data) => adminRequest(`/teachers/${id}`, { method: 'PUT', body: data }),
  resetTeacherPassword: (id, password) => adminRequest(`/teachers/${id}/password`, { method: 'POST', body: { password } }),
  classes: () => adminRequest('/classes'),
  addClass: (data) => adminRequest('/classes', { method: 'POST', body: data }),
  updateClass: (id, data) => adminRequest(`/classes/${id}`, { method: 'PUT', body: data }),
  deleteClass: (id) => adminRequest(`/classes/${id}`, { method: 'DELETE' }),
  classTeams: (id) => adminRequest(`/classes/${id}/teams`),
  students: (classId, query = '', offset = 0) => adminRequest(
    `/students?class_id=${classId}&query=${encodeURIComponent(query)}&limit=100&offset=${offset}`
  ),
  addStudent: (data) => adminRequest('/students', { method: 'POST', body: data }),
  updateStudent: (id, data) => adminRequest(`/students/${id}`, { method: 'PUT', body: data }),
  deleteStudent: (id) => adminRequest(`/students/${id}`, { method: 'DELETE' }),
  resetStudentCode: (id) => adminRequest(`/students/${id}/password`, { method: 'POST' }),
};

const classApi = {
  list: () => api('/classes'),
  get: (id) => api(`/classes/${id}`),
  create: (data) => api('/classes', { method: 'POST', body: data }),
  delete: (id) => api(`/classes/${id}`, { method: 'DELETE' }),
  importExcel: (classId, file) => {
    const form = new FormData();
    form.append('file', file);
    return api(`/classes/${classId}/import-excel`, { method: 'POST', body: form });
  },
  listTeams: (classId) => api(`/classes/${classId}/teams`),
  createTeam: (classId, data) =>
    api(`/classes/${classId}/teams`, { method: 'POST', body: data }),
  listStudents: (classId) => api(`/classes/${classId}/students`),
  createStudent: (classId, data) =>
    api(`/classes/${classId}/students`, { method: 'POST', body: data }),
};

const teamApi = {
  get: (id) => api(`/teams/${id}`),
  update: (id, name) => api(`/teams/${id}?name=${encodeURIComponent(name)}`, { method: 'PUT' }),
  delete: (id) => api(`/teams/${id}`, { method: 'DELETE' }),
  members: (id) => api(`/teams/${id}/members`),
  qrcode: (id) => api(`/teams/${id}/qrcode`),
};

const studentApi = {
  login: (teamId, identifier, password) =>
    studentRequest('/auth/student-login', { method: 'POST', body: { team_id: teamId, identifier, password } }),
  logout: () => studentRequest('/auth/student-logout', { method: 'POST' }),
  changePassword: (currentPassword, newPassword) =>
    studentRequest('/auth/student-password', {
      method: 'POST', body: { current_password: currentPassword, new_password: newPassword }
    }),
  me: () => studentRequest('/auth/student-me'),
  submissions: (teamId) => studentRequest(`/practices/student/team/${teamId}`),
  submit: (teamId, title, content, files) => {
    const form = new FormData();
    form.append('title', title);
    form.append('content', content);
    for (const file of files) form.append('files', file);
    return studentRequest(`/practices/student/team/${teamId}`, { method: 'POST', body: form });
  },
  get: (id) => api(`/students/${id}`),
  update: (id, data) => api(`/students/${id}`, { method: 'PUT', body: data }),
  delete: (id) => api(`/students/${id}`, { method: 'DELETE' }),
  resetLoginCode: (id) => api(`/students/${id}/password`, { method: 'POST' }),
};

const practiceApi = {
  listByTeam: (teamId) => api(`/practices/team/${teamId}`),
  get: (id) => api(`/practices/${id}`),
  listEvaluations: (id) => api(`/practices/${id}/evaluations`),
  create: (teamId, title, content, memberWorks, files = []) => {
    const form = new FormData();
    form.append('title', title);
    form.append('content', content);
    form.append('member_works', JSON.stringify(memberWorks));
    for (const f of files) form.append('files', f);
    return api(`/practices/team/${teamId}`, { method: 'POST', body: form });
  },
  delete: (id) => api(`/practices/${id}`, { method: 'DELETE' }),
  reanalyze: (id) => api(`/practices/${id}/ai-reanalyze`, { method: 'POST' }),
  setPublication: (id, published) => api(`/practices/${id}/publication?published=${published}`, { method: 'PUT' }),
  evaluate: (id, score, comment) =>
    api(`/practices/${id}/evaluate`, { method: 'POST', body: { score, comment } }),
  createEvaluation: (id, targetType, targetId, score, comment) =>
    api(`/practices/${id}/evaluations`, { method: 'POST', body: { target_type: targetType, target_id: targetId, score, comment } }),
  update: (id, title, content, memberWorks) => {
    const form = new FormData();
    form.append('title', title);
    form.append('content', content);
    form.append('member_works', JSON.stringify(memberWorks));
    return api(`/practices/${id}`, { method: 'PUT', body: form });
  },
};

async function checkHealth() {
  try {
    await api('/health');
    return true;
  } catch {
    return false;
  }
}
