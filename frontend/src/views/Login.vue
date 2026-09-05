<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api/auth'
import { useTheme } from '../composables/useTheme'

const router = useRouter()
const { currentTheme, setTheme } = useTheme()
const themes = { 'sage-green': '#A8B5A0', 'dreamy-blue': '#99A4BC', 'grey-pink': '#D4A5A5', 'grey-purple': '#B5A8C0', 'warm-apricot': '#D4B896' }
const activeTab = ref('login')
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '', confirmPassword: '' })
const loginLoading = ref(false)
const registerLoading = ref(false)
const registerFormRef = ref(null)
function validatePassword(_rule, value, callback) { if (!value || value.length < 8 || !/[a-zA-Z]/.test(value) || !/\d/.test(value)) callback(new Error('密码需至少8位且包含数字和字母')); else callback() }
function validateConfirmPassword(_rule, value, callback) { if (!value || value !== registerForm.password) callback(new Error('两次输入的密码不一致')); else callback() }
const registerRules = { username: [{ required: true, message: '请输入用户名', trigger: 'blur' }], password: [{ required: true, validator: validatePassword, trigger: 'blur' }], confirmPassword: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }] }
async function handleLogin() { if (!loginForm.username || !loginForm.password) return ElMessage.warning('请输入用户名和密码'); loginLoading.value = true; try { const res = await login(loginForm); localStorage.setItem('token', res.access_token); localStorage.setItem('user', JSON.stringify(res.user)); ElMessage.success('登录成功'); router.push('/') } catch (err) { ElMessage.error(err.response?.data?.detail || err.message || '登录失败') } finally { loginLoading.value = false } }
async function handleRegister() { if (!registerFormRef.value) return; try { await registerFormRef.value.validate() } catch { return } registerLoading.value = true; try { await register({ username: registerForm.username, password: registerForm.password }); const res = await login({ username: registerForm.username, password: registerForm.password }); localStorage.setItem('token', res.access_token); localStorage.setItem('user', JSON.stringify(res.user)); ElMessage.success('注册成功'); router.push('/guide') } catch (err) { ElMessage.error(err.response?.data?.detail || err.message || '注册失败') } finally { registerLoading.value = false } }
</script>
<template>
  <div class="login-page">
    <section class="login-intro">
      <div class="intro-content"><div class="intro-mark">🌿</div><h1>心情守护</h1><p>记录心情，也记录生活。</p><div class="intro-line"></div><small>温柔地对待自己的每一天</small></div>
    </section>
    <section class="login-panel">
      <div class="login-card">
        <h2>{{ activeTab === 'login' ? '欢迎回来' : '创建账号' }}</h2><p class="subtitle">{{ activeTab === 'login' ? '登录你的心情守护账号' : '从今天开始，认识自己的情绪' }}</p>
        <el-form v-if="activeTab === 'login'" @submit.prevent="handleLogin" label-position="top"><el-form-item label="用户名"><el-input v-model="loginForm.username" placeholder="请输入用户名" /></el-form-item><el-form-item label="密码"><el-input v-model="loginForm.password" type="password" placeholder="请输入密码（至少 8 位，需含数字和字母）" show-password /></el-form-item><el-button class="submit-button" native-type="submit" type="primary" :loading="loginLoading">登录</el-button></el-form>
        <el-form v-else ref="registerFormRef" :model="registerForm" :rules="registerRules" label-position="top"><el-form-item label="用户名" prop="username"><el-input v-model="registerForm.username" placeholder="请输入用户名" /></el-form-item><el-form-item label="密码" prop="password"><el-input v-model="registerForm.password" type="password" placeholder="至少 8 位，需含数字和字母" show-password /></el-form-item><el-form-item label="确认密码" prop="confirmPassword"><el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码" show-password /></el-form-item><el-button class="submit-button" type="primary" :loading="registerLoading" @click="handleRegister">注册</el-button></el-form>
        <button class="switch-link" @click="activeTab = activeTab === 'login' ? 'register' : 'login'">{{ activeTab === 'login' ? '还没有账号？立即注册' : '已有账号？返回登录' }}</button>
      </div>
      <div class="theme-selector"><span>主题</span><button v-for="(color, name) in themes" :key="name" class="theme-dot" :class="{ active: currentTheme === name }" :style="{ background: color }" :aria-label="`切换${name}主题`" @click="setTheme(name)" /></div>
    </section>
  </div>
</template>
<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(360px, .86fr) minmax(460px, 1.14fr);
  background: var(--app-bg);
}

.login-intro {
  display: flex;
  align-items: center;
  padding: clamp(48px, 8vw, 120px);
  color: var(--app-text);
  background: var(--app-primary-light);
}

.intro-content { max-width: 360px; }
.intro-mark { margin-bottom: 22px; font-size: 44px; line-height: 1; }
.login-intro h1 { margin: 0; font-size: clamp(34px, 4vw, 48px); font-weight: 600; letter-spacing: 0; }
.login-intro p { margin: 18px 0 0; color: var(--app-text); font-size: 18px; }
.intro-line { width: 52px; margin: 28px 0 18px; border-top: 2px solid var(--app-primary-dark); }
.login-intro small { color: var(--app-text-light); font-size: 14px; }

.login-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 48px 32px;
  background: var(--app-bg);
}

.login-card {
  width: min(390px, 100%);
  padding: 38px 40px 32px;
  border: 1px solid var(--app-border);
  border-radius: 20px;
  background: var(--app-card-bg);
  box-shadow: 0 10px 30px rgba(74, 82, 72, .08);
}

.login-card h2 { margin: 0; color: var(--app-text); font-size: 28px; font-weight: 600; }
.subtitle { margin: 10px 0 28px; color: var(--app-text-light); font-size: 14px; }
.login-card :deep(.el-form-item) { margin-bottom: 20px; }
.login-card :deep(.el-form-item__label) { padding-bottom: 7px; color: var(--app-text); font-size: 14px; }
.login-card :deep(.el-input__wrapper) { min-height: 44px; border-radius: 10px; background: var(--app-bg); box-shadow: inset 0 0 0 1px var(--app-border); }
.login-card :deep(.el-input__wrapper.is-focus) { box-shadow: inset 0 0 0 2px var(--app-primary); }
.login-card :deep(.el-input__inner) { color: var(--app-text); }
.login-card :deep(.el-button.submit-button) { width: 100%; height: 46px; margin-top: 4px; border: 0; border-radius: 10px; background: var(--app-primary); color: var(--app-card-bg); font-size: 15px; font-weight: 600; }
.login-card :deep(.el-button.submit-button:hover) { background: var(--app-primary-dark); }
.switch-link { display: block; margin: 22px auto 0; padding: 0; border: 0; background: transparent; color: var(--app-primary-dark); font-size: 14px; cursor: pointer; }
.switch-link:hover { color: var(--app-primary); text-decoration: underline; }
.theme-selector { display: flex; align-items: center; gap: 12px; color: var(--app-text-light); font-size: 13px; }
.theme-selector .theme-dot { width: 18px; height: 18px; padding: 0; border: 2px solid transparent; border-radius: 50%; cursor: pointer; }
.theme-selector .theme-dot.active { border-color: var(--app-text); box-shadow: 0 0 0 3px var(--app-bg); }

@media (max-width: 700px) {
  .login-page { display: block; }
  .login-intro { min-height: 250px; padding: 42px 30px; }
  .login-intro h1 { font-size: 36px; }
  .login-intro p { font-size: 16px; }
  .login-panel { min-height: calc(100vh - 250px); padding: 34px 18px; }
  .login-card { padding: 30px 24px 26px; }
}
</style>
