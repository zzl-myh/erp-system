<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <span>个人信息</span>
        </div>
      </template>
      
      <div class="profile-content" v-loading="loading">
        <div class="avatar-section">
          <el-avatar :size="80" icon="UserFilled" />
          <div class="user-name">{{ userStore.name || userStore.username }}</div>
          <div class="user-role">
            <el-tag v-for="role in userStore.userInfo?.roles" :key="role.code" size="small" style="margin-right: 4px">
              {{ role.name }}
            </el-tag>
          </div>
        </div>
        
        <el-divider />
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户名">
            {{ userStore.userInfo?.username }}
          </el-descriptions-item>
          <el-descriptions-item label="姓名">
            {{ userStore.userInfo?.name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="手机号">
            {{ userStore.userInfo?.mobile || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">
            {{ userStore.userInfo?.email || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="userStore.userInfo?.status === 1 ? 'success' : 'danger'">
              {{ userStore.userInfo?.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ userStore.userInfo?.created_at || '-' }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="action-buttons">
          <el-button type="primary" @click="handleEdit">编辑信息</el-button>
        </div>
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑个人信息" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="mobile">
          <el-input v-model="form.mobile" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores'
import { updateUser } from '@/api/user'

const userStore = useUserStore()
const loading = ref(false)
const editDialogVisible = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  mobile: '',
  email: ''
})

const rules: FormRules = {
  mobile: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

onMounted(async () => {
  loading.value = true
  try {
    await userStore.fetchUserInfo()
  } finally {
    loading.value = false
  }
})

function handleEdit() {
  form.name = userStore.userInfo?.name || ''
  form.mobile = userStore.userInfo?.mobile || ''
  form.email = userStore.userInfo?.email || ''
  editDialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitLoading.value = true
    
    const userId = userStore.userInfo?.id
    if (!userId) {
      ElMessage.error('用户信息异常')
      return
    }
    
    const res = await updateUser(userId, {
      name: form.name || undefined,
      mobile: form.mobile || undefined,
      email: form.email || undefined
    })
    
    if (res.success) {
      ElMessage.success('更新成功')
      editDialogVisible.value = false
      // 刷新用户信息
      await userStore.fetchUserInfo()
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (error) {
    // 校验失败
  } finally {
    submitLoading.value = false
  }
}
</script>

<style scoped>
.profile-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.profile-card {
  border-radius: 8px;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
}

.avatar-section {
  text-align: center;
  padding: 20px 0;
}

.user-name {
  margin-top: 16px;
  font-size: 20px;
  font-weight: 600;
}

.user-role {
  margin-top: 8px;
}

.action-buttons {
  margin-top: 24px;
  text-align: center;
}
</style>
