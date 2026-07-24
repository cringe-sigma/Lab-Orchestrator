import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 自动带 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 时跳回登录
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// ===== Auth =====
export interface LoginData {
  username: string
  password: string
}

export interface AuthResult {
  access_token: string
  user_id: number
  username: string
  role: string
}

export const authApi = {
  login: (data: LoginData) => api.post<AuthResult>('/auth/login', data),
  register: (data: LoginData & { display_name?: string }) =>
    api.post<AuthResult>('/auth/register', data),
  me: () => api.get('/auth/me'),
}

// ===== Boards =====
export interface BoardData {
  id: number
  name: string
  board_type: string
  status: string
  conn_type: string
  host: string
  port: number
  serial_port: string
  board_token: string | null
  tags: string
  description: string
  locked_by: number | null
  is_active: boolean
  last_heartbeat: string | null
}

export const boardApi = {
  list: () => api.get<BoardData[]>('/boards/'),
  get: (id: number) => api.get<BoardData>(`/boards/${id}`),
  create: (data: Partial<BoardData>) => api.post<BoardData>('/boards/', data),
  check: (id: number) => api.post(`/boards/${id}/check`),
  exec: (id: number, command: string, password?: string) =>
    api.post(`/boards/${id}/exec`, { command, password }),
}

// ===== Experiments =====
export interface ExperimentData {
  id: number
  board_id: number
  name: string
  description: string
  steps: string
  status: string
  result_summary: string
  result_data: string
  is_ai_driven: boolean
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export const experimentApi = {
  list: () => api.get<ExperimentData[]>('/experiments/'),
  get: (id: number) => api.get<ExperimentData>(`/experiments/${id}`),
  create: (data: Partial<ExperimentData> & { board_id: number; name: string }) =>
    api.post<ExperimentData>('/experiments/', data),
  run: (id: number) => api.post(`/experiments/${id}/run`),
  runStep: (id: number, step: number) => api.post(`/experiments/${id}/step/${step}`),
  aiChat: (boardId: number, message: string) =>
    api.post(`/experiments/ai-chat/${boardId}`, { message }),
}

// ===== Bookings =====
export interface BookingData {
  id: number
  board_id: number
  title: string
  start_time: string
  end_time: string
  status: string
  created_at: string
}

export const bookingApi = {
  list: () => api.get<BookingData[]>('/bookings/'),
  create: (data: { board_id: number; title?: string; start_time: string; end_time: string }) =>
    api.post('/bookings/', data),
  cancel: (id: number) => api.post(`/bookings/${id}/cancel`),
}

// ===== Health =====
export const healthApi = {
  check: () => api.get('/health'),
}

export default api
