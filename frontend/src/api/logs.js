import http from './http'


export async function createLog(payload) {
  const { data } = await http.post('/logs', payload)
  return data
}


export async function deleteLog(id) {
  const { data } = await http.delete(`/logs/${id}`)
  return data
}


export async function getLogs(params) {
  const { data } = await http.get('/logs', { params })
  return data
}


export async function updateLog(id, payload) {
  const { data } = await http.put(`/logs/${id}`, payload)
  return data
}


export async function analyzeLog(content) {
  const { data } = await http.post('/analyze', { content })
  return data
}