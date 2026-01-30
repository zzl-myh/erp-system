<template>
  <div class="user-management">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="queryForm" inline>
        <el-form-item label="关键词">
          <el-input
            v-model="queryForm.keyword"
            placeholder="用户名/姓名/手机号"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryForm.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作栏 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>用户列表</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon> 新增用户
          </el-button>
        </div>
      </template>

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="name" label="姓名" width="120">
          <template #default="{ row }">
            {{ row.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="mobile" label="手机号" width="130">
          <template #default="{ row }">
            {{ row.mobile || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">
            {{ row.email || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="roles" label="角色" width="150">
          <template #default="{ row }">
            <el-tag 
              v-for="role in row.roles" 
              :key="role.code" 
              size="small" 
              class="role-tag"
            >
              {{ role.name }}
            </el-tag>
            <span v-if="!row.roles?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button type="warning" link size="small" @click="handleAssignRole(row)">
              分配角色
            </el-button>
            <el-button type="info" link size="small" @click="handleResetPassword(row)">
              重置密码
            </el-button>
            <el-button 
              :type="row.status === 1 ? 'danger' : 'success'" 
              link 
              size="small" 
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 1 ? '禁用' : '启用' }}
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="queryForm.page"
          v-model:page-size="queryForm.size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogTitle" 
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form 
        ref="formRef" 
        :model="form" 
        :rules="rules" 
        label-width="80px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="form.username" 
            :disabled="isEdit"
            placeholder="请输入用户名"
          />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="mobile">
          <el-input v-model="form.mobile" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 分配角色对话框 -->
    <el-dialog 
      v-model="roleDialogVisible" 
      title="分配角色" 
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px">
        <el-form-item label="用户">
          <span>{{ currentUser?.username }} ({{ currentUser?.name || '-' }})</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-checkbox-group v-model="selectedRoles">
            <el-checkbox 
              v-for="role in roleList" 
              :key="role.code" 
              :value="role.code"
            >
              {{ role.name }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="roleSubmitLoading" @click="handleRoleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { 
  getUserList, 
  createUser, 
  updateUser, 
  assignRoles, 
  getRoleList,
  resetPassword,
  deleteUser,
  type UserInfo,
  type UserCreate,
  type UserUpdate,
  type Role
} from '@/api/user'

// 查询表单
const queryForm = reactive({
  keyword: '',
  status: undefined as number | undefined,
  page: 1,
  size: 20
})

// 表格数据
const tableData = ref<UserInfo[]>([])
const total = ref(0)
const loading = ref(false)

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('新增用户')
const isEdit = ref(false)
const formRef = ref<FormInstance>()
const submitLoading = ref(false)

// 表单数据
const form = reactive<UserCreate & { id?: number; status?: number }>({
  username: '',
  password: '',
  name: '',
  mobile: '',
  email: '',
  status: 1
})

// 表单校验规则
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  mobile: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ]
}

// 角色相关
const roleDialogVisible = ref(false)
const roleList = ref<Role[]>([])
const selectedRoles = ref<string[]>([])
const currentUser = ref<UserInfo | null>(null)
const roleSubmitLoading = ref(false)

// 格式化日期
function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 查询列表
async function fetchList() {
  loading.value = true
  try {
    const res = await getUserList(queryForm)
    if (res.success && res.data) {
      tableData.value = res.data.items
      total.value = res.data.total
    }
  } finally {
    loading.value = false
  }
}

// 加载角色列表
async function fetchRoleList() {
  const res = await getRoleList()
  if (res.success && res.data) {
    roleList.value = res.data
  }
}

// 搜索
function handleSearch() {
  queryForm.page = 1
  fetchList()
}

// 重置
function handleReset() {
  queryForm.keyword = ''
  queryForm.status = undefined
  queryForm.page = 1
  handleSearch()
}

// 新增
function handleAdd() {
  isEdit.value = false
  dialogTitle.value = '新增用户'
  Object.assign(form, {
    id: undefined,
    username: '',
    password: '',
    name: '',
    mobile: '',
    email: '',
    status: 1
  })
  dialogVisible.value = true
}

// 编辑
function handleEdit(row: UserInfo) {
  isEdit.value = true
  dialogTitle.value = '编辑用户'
  Object.assign(form, {
    id: row.id,
    username: row.username,
    password: '',
    name: row.name || '',
    mobile: row.mobile || '',
    email: row.email || '',
    status: row.status
  })
  dialogVisible.value = true
}

// 提交表单
async function handleSubmit() {
  await formRef.value?.validate()
  
  submitLoading.value = true
  try {
    if (isEdit.value) {
      const updateData: UserUpdate = {
        name: form.name,
        mobile: form.mobile,
        email: form.email,
        status: form.status
      }
      const res = await updateUser(form.id!, updateData)
      if (res.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        fetchList()
      }
    } else {
      const createData: UserCreate = {
        username: form.username,
        password: form.password,
        name: form.name,
        mobile: form.mobile,
        email: form.email
      }
      const res = await createUser(createData)
      if (res.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        fetchList()
      }
    }
  } finally {
    submitLoading.value = false
  }
}

// 切换状态
async function handleToggleStatus(row: UserInfo) {
  const newStatus = row.status === 1 ? 0 : 1
  const action = newStatus === 1 ? '启用' : '禁用'
  
  await ElMessageBox.confirm(
    `确定要${action}用户 "${row.username}" 吗？`,
    '提示',
    { type: 'warning' }
  )
  
  const res = await updateUser(row.id, { status: newStatus })
  if (res.success) {
    ElMessage.success(`${action}成功`)
    fetchList()
  }
}

// 重置密码
async function handleResetPassword(row: UserInfo) {
  const { value } = await ElMessageBox.prompt(
    `请输入用户 "${row.username}" 的新密码`,
    '重置密码',
    {
      inputPattern: /^.{6,}$/,
      inputErrorMessage: '密码至少6位',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    }
  )
  
  if (value) {
    const res = await resetPassword({ user_id: row.id, new_password: value })
    if (res.success) {
      ElMessage.success('密码重置成功')
    }
  }
}

// 删除用户
async function handleDelete(row: UserInfo) {
  await ElMessageBox.confirm(
    `确定要删除用户 "${row.username}" 吗？此操作不可恢复！`,
    '警告',
    { type: 'error' }
  )
  
  const res = await deleteUser(row.id)
  if (res.success) {
    ElMessage.success('删除成功')
    fetchList()
  }
}

// 分配角色
function handleAssignRole(row: UserInfo) {
  currentUser.value = row
  selectedRoles.value = row.roles?.map(r => r.code) || []
  roleDialogVisible.value = true
}

// 提交角色分配
async function handleRoleSubmit() {
  if (!currentUser.value) return
  
  roleSubmitLoading.value = true
  try {
    const res = await assignRoles({
      user_id: currentUser.value.id,
      roles: selectedRoles.value
    })
    if (res.success) {
      ElMessage.success('角色分配成功')
      roleDialogVisible.value = false
      fetchList()
    }
  } finally {
    roleSubmitLoading.value = false
  }
}

onMounted(() => {
  fetchList()
  fetchRoleList()
})
</script>

<style lang="scss" scoped>
.user-management {
  .search-card {
    margin-bottom: 16px;
    
    :deep(.el-card__body) {
      padding-bottom: 0;
    }
  }

  .table-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .role-tag {
    margin-right: 4px;
    margin-bottom: 4px;
  }

  .pagination-wrapper {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
