import http from './http'


export async function loadPreferences() {
  const { data } = await http.get('/preferences')
  return data
}


export async function savePreferences(payload) {
  const { data } = await http.post('/preferences', payload)
  return data
}