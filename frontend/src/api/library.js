import http from './http'


export async function getLibraryMovies() {
  const { data } = await http.get('/library/movies')
  return data
}


export async function getLibraryBooks() {
  const { data } = await http.get('/library/books')
  return data
}


export async function addLibraryReview(itemType, title, payload) {
  const encodedTitle = encodeURIComponent(title)
  const { data } = await http.post(`/library/${itemType}/${encodedTitle}/reviews`, payload)
  return data
}


export async function getBookReviews(title) {
  const encodedTitle = encodeURIComponent(title)
  const { data } = await http.get(`/library/books/${encodedTitle}/reviews`)
  return data
}


export async function getMovieReviews(title) {
  const encodedTitle = encodeURIComponent(title)
  const { data } = await http.get(`/library/movies/${encodedTitle}/reviews`)
  return data
}


export async function addLibraryItem(payload) {
  const { data } = await http.post('/library/manual_add', payload)
  return data
}


export async function finishLibraryBook(id) {
  const { data } = await http.post(`/library/finish_book/${id}`)
  return data
}


export async function deleteLibraryItem(id) {
  const { data } = await http.delete(`/library/${id}`)
  return data
}
