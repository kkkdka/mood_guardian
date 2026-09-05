import http from './http'


export async function listSchedules({ start_date, end_date } = {}) {
  const { data } = await http.get('/schedules', {
    params: { start_date, end_date },
  })
  return data
}


export async function createSchedule(payload) {
  const { data } = await http.post('/schedules', payload)
  return data
}


export async function updateSchedule(id, payload) {
  const { data } = await http.put(`/schedules/${id}`, payload)
  return data
}


export async function deleteSchedule(id) {
  const { data } = await http.delete(`/schedules/${id}`)
  return data
}


export async function toggleSchedule(id) {
  const { data } = await http.patch(`/schedules/${id}/toggle_completed`)
  return data
}


export async function completeAllSchedules({ date } = {}) {
  const { data } = await http.patch('/schedules/complete_all', null, {
    params: { date },
  })
  return data
}