import { createRouter, createWebHistory } from 'vue-router'
import Write from '../views/Write.vue'
import Stats from '../views/Stats.vue'
import Schedule from '../views/Schedule.vue'
import Heal from '../views/Heal.vue'
import Login from '../views/Login.vue'
import RegisterGuide from '../views/RegisterGuide.vue'
import Settings from '../views/Settings.vue'
import Library from '../views/Library.vue'



const routes = [
  { path: '/', redirect: '/diary' }, 
  { path: '/login', name: 'login', component: Login },
  { path: '/guide', name: 'guide', component: RegisterGuide },
  { path: '/settings', name: 'settings', component: Settings },
  { path: '/library', name: 'library', component: Library },
  { path: '/diary', name: 'diary', component: Write },
  { path: '/stats', name: 'stats', component: Stats },
  { path: '/schedule', name: 'schedule', component: Schedule },
  { path: '/heal', name: 'heal', component: Heal },
]

const router = createRouter({
  history: createWebHistory(), 
  routes,
})



const WHITE_LIST = ['/login']

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')

  
  if (WHITE_LIST.includes(to.path)) {
    
    if (token && to.path === '/login') {
      next('/')
      return
    }
    next()
    return
  }

  
  if (!token) {
    next('/login')
    return
  }

  next()
})

export default router
