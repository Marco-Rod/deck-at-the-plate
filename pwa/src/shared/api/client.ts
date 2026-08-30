import axios from 'axios'
import { API_BASE_URL } from './config'
import { setupInterceptors } from './interceptors'

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

setupInterceptors(http)
