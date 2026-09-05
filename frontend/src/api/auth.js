import http from './http'


export async function register({ username, password }) {
  const { data } = await http.post('/auth/register', { username, password })
  return data
}


export async function login({ username, password }) {
  const { data } = await http.post('/auth/login', { username, password })
  return data
}


export async function getMe() {
  const { data } = await http.get('/auth/me')
  return data
}