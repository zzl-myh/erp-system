<template>
  <div class="org-container">
    <!-- 头部操作区 -->
    <div class="header-actions">
      <el-button type="primary" @click="handleAdd(null)">
        <el-icon><Plus /></el-icon>
        新增组织
      </el-button>
      <el-button @click="expandAll">全部展开</el-button>
      <el-button @click="collapseAll">全部收起</el-button>
    </div>

    <!-- 组织树表 -->
    <el-table
      ref="tableRef"
      :data="orgTree"
      v-loading="loading"
      row-key="id"
      border
      default-expand-all
    >
      <el-table-column prop="name" label="组织名称" width="250" />
      <el-table-column prop="code" label="组织编码" width="150" />
      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="getTypeTag(row.type)">{{ getTypeName(row.type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handleAdd(row)">新增子级</el-button>
          <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
          <el-button 
            type="danger" 
            link 
            @click="handleDelete(row)"
            :disabled="row.children && row.children.length > 0"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑组织' : '新增组织'"
      width="500px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="上级组织">
          <el-input :value="parentName" disabled />
        </el-form-item>
        <el-form-item label="组织编码" prop="code">
          <el-input 
            v-model="formData.code" 
            placeholder="请输入组织编码"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item label="组织名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入组织名称" />
        </el-form-item>
        <el-form-item label="组织类型" prop="type">
          <el-select v-model="formData.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="总部" value="HQ" />
            <el-option label="区域" value="REGION" />
            <el-option label="门店" value="STORE" />
            <el-option label="部门" value="DEPT" />
            <el-option label="仓库" value="WAREHOUSE" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status" v-if="isEdit">
          <el-radio-group v-model="formData.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type TableInstance } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getOrgList, createOrg, updateOrg, deleteOrg, type Org, type OrgCreate, type OrgUpdate } from '@/api/user'

// 扩展 Org 类型支持 children
interface OrgNode extends Org {
  children?: OrgNode[]
}

// 状态
const loading = ref(false)
const orgList = ref<Org[]>([])
const orgTree = ref<OrgNode[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const tableRef = ref<TableInstance>()
const currentOrg = ref<Org | null>(null)
const parentOrg = ref<Org | null>(null)

// 表单数据
const formData = reactive({
  code: '',
  name: '',
  type: 'STORE',
  parent_id: 0,
  status: 1
})

// 表单校验规则
const formRules: FormRules = {
  code: [
    { required: true, message: '请输入组织编码', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入组织名称', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择组织类型', trigger: 'change' }
  ]
}

// 上级组织名称
const parentName = computed(() => {
  if (parentOrg.value) {
    return parentOrg.value.name
  }
  return '无（顶级组织）'
})

// 获取类型名称
function getTypeName(type: string): string {
  const typeMap: Record<string, string> = {
    'HQ': '总部',
    'REGION': '区域',
    'STORE': '门店',
    'DEPT': '部门',
    'WAREHOUSE': '仓库'
  }
  return typeMap[type] || type
}

// 获取类型标签样式
function getTypeTag(type: string): string {
  const tagMap: Record<string, string> = {
    'HQ': 'danger',
    'REGION': 'warning',
    'STORE': 'success',
    'DEPT': 'info',
    'WAREHOUSE': ''
  }
  return tagMap[type] || ''
}

// 构建树形结构
function buildTree(list: Org[]): OrgNode[] {
  const map = new Map<number, OrgNode>()
  const tree: OrgNode[] = []

  // 先创建所有节点
  list.forEach(item => {
    map.set(item.id, { ...item, children: [] })
  })

  // 构建父子关系
  list.forEach(item => {
    const node = map.get(item.id)!
    if (item.parent_id === 0 || !map.has(item.parent_id)) {
      tree.push(node)
    } else {
      const parent = map.get(item.parent_id)!
      parent.children = parent.children || []
      parent.children.push(node)
    }
  })

  return tree
}

// 获取组织列表
async function fetchList() {
  loading.value = true
  try {
    const res = await getOrgList()
    if (res.success) {
      orgList.value = res.data || []
      orgTree.value = buildTree(orgList.value)
    } else {
      ElMessage.error(res.message || '获取组织列表失败')
    }
  } catch (error) {
    ElMessage.error('获取组织列表失败')
  } finally {
    loading.value = false
  }
}

// 展开/收起
function expandAll() {
  toggleRowExpansion(orgTree.value, true)
}

function collapseAll() {
  toggleRowExpansion(orgTree.value, false)
}

function toggleRowExpansion(rows: OrgNode[], expanded: boolean) {
  rows.forEach(row => {
    tableRef.value?.toggleRowExpansion(row, expanded)
    if (row.children && row.children.length > 0) {
      toggleRowExpansion(row.children, expanded)
    }
  })
}

// 重置表单
function resetForm() {
  formData.code = ''
  formData.name = ''
  formData.type = 'STORE'
  formData.parent_id = 0
  formData.status = 1
  currentOrg.value = null
  parentOrg.value = null
}

// 新增组织
function handleAdd(parent: OrgNode | null) {
  resetForm()
  isEdit.value = false
  parentOrg.value = parent
  formData.parent_id = parent?.id || 0
  dialogVisible.value = true
}

// 编辑组织
function handleEdit(row: Org) {
  currentOrg.value = row
  isEdit.value = true
  // 查找父级
  parentOrg.value = orgList.value.find((o: Org) => o.id === row.parent_id) || null
  formData.code = row.code
  formData.name = row.name
  formData.type = row.type
  formData.parent_id = row.parent_id
  formData.status = row.status
  dialogVisible.value = true
}

// 删除组织
async function handleDelete(row: Org) {
  try {
    await ElMessageBox.confirm(
      `确定要删除组织 "${row.name}" 吗？删除后不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    const res = await deleteOrg(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchList()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    // 用户取消
  }
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitLoading.value = true

    if (isEdit.value && currentOrg.value) {
      // 编辑
      const updateData: OrgUpdate = {
        name: formData.name,
        type: formData.type,
        status: formData.status
      }
      const res = await updateOrg(currentOrg.value.id, updateData)
      if (res.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        fetchList()
      } else {
        ElMessage.error(res.message || '更新失败')
      }
    } else {
      // 新增
      const createData: OrgCreate = {
        code: formData.code,
        name: formData.name,
        type: formData.type,
        parent_id: formData.parent_id
      }
      const res = await createOrg(createData)
      if (res.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        fetchList()
      } else {
        ElMessage.error(res.message || '创建失败')
      }
    }
  } catch (error) {
    // 校验失败
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.org-container {
  padding: 20px;
}

.header-actions {
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
}
</style>
