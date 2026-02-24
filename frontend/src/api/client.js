import axios from 'axios'
import toast from 'react-hot-toast'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor — normalise error shape
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const data = error.response?.data

    // Backend returns { error: { code, message, details } }
    if (data?.error?.message) {
      toast.error(data.error.message)
    } else if (status === 404) {
      toast.error('Resource not found.')
    } else if (status === 422) {
      toast.error('Validation error. Please check your inputs.')
    } else if (status >= 500) {
      toast.error('Server error. Please try again.')
    } else if (!error.response) {
      toast.error('Cannot reach server. Is the backend running?')
    }

    return Promise.reject(error)
  },
)

export default client
