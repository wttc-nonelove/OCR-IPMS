import axios from 'axios'
import { ElMessage } from 'element-plus'

export const http = axios.create({
  baseURL: '/api/v1'
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '请求失败'
    const message = Array.isArray(detail) ? detail.map((item: any) => item.msg || JSON.stringify(item)).join('；') : detail
    ElMessage.error(message)
    return Promise.reject(error)
  }
)
