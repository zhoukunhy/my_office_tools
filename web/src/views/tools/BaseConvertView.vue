<script setup lang="ts">
import { reactive, ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import ToolHeader from '@/components/tools/ToolHeader.vue'

type TabName = 'base' | 'unit'

const activeTab = ref<TabName>('base')

// ==================== 进制转换 ====================
type BaseField = 'dec' | 'bin' | 'oct' | 'hex'

const baseMeta: Record<BaseField, { label: string; radix: number }> = {
  dec: { label: '十进制', radix: 10 },
  bin: { label: '二进制', radix: 2 },
  oct: { label: '八进制', radix: 8 },
  hex: { label: '十六进制', radix: 16 }
}

const baseOrder: BaseField[] = ['dec', 'bin', 'oct', 'hex']

const baseValues = reactive<Record<BaseField, string>>({
  dec: '',
  bin: '',
  oct: '',
  hex: ''
})
const baseErrors = reactive<Record<BaseField, string>>({
  dec: '',
  bin: '',
  oct: '',
  hex: ''
})

const DIGITS = '0123456789abcdefghijklmnopqrstuvwxyz'

/** 解析任意进制字符串为 BigInt，非法返回 null（支持大数） */
function parseBigInt(input: string, radix: number): bigint | null {
  let s = input.trim()
  if (!s) return null
  let negative = false
  if (s[0] === '-' || s[0] === '+') {
    negative = s[0] === '-'
    s = s.slice(1)
  }
  if (!s) return null
  const valid = DIGITS.slice(0, radix)
  const b = BigInt(radix)
  let result = 0n
  for (const ch of s.toLowerCase()) {
    const idx = valid.indexOf(ch)
    if (idx === -1) return null
    result = result * b + BigInt(idx)
  }
  return negative ? -result : result
}

/** BigInt 转任意进制字符串 */
function bigIntToString(val: bigint, radix: number): string {
  if (val === 0n) return '0'
  let negative = false
  if (val < 0n) {
    negative = true
    val = -val
  }
  const b = BigInt(radix)
  let out = ''
  while (val > 0n) {
    out = DIGITS[Number(val % b)] + out
    val = val / b
  }
  return negative ? '-' + out : out
}

let baseSyncing = false

function onBaseInput(field: BaseField, val: string) {
  baseValues[field] = val
  if (baseSyncing) return
  const raw = val.trim()
  if (!raw) {
    baseSyncing = true
    for (const f of baseOrder) {
      if (f !== field) {
        baseValues[f] = ''
        baseErrors[f] = ''
      }
    }
    baseSyncing = false
    return
  }
  const num = parseBigInt(raw, baseMeta[field].radix)
  if (num === null) {
    baseErrors[field] = `无效的${baseMeta[field].label}输入`
    return
  }
  baseErrors[field] = ''
  baseSyncing = true
  for (const f of baseOrder) {
    if (f !== field) {
      baseValues[f] = bigIntToString(num, baseMeta[f].radix)
      baseErrors[f] = ''
    }
  }
  baseSyncing = false
}

function copyText(text: string) {
  if (!text) {
    ElMessage.warning('内容为空')
    return
  }
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}

// 初始化示例
onBaseInput('dec', '255')

// ==================== 单位换算 ====================
interface UnitDef {
  name: string
  symbol: string
  /** 相对基准单位的系数（基准单位 factor=1） */
  factor: number
}

interface CategoryDef {
  id: string
  name: string
  base: string
  units: UnitDef[]
  isTemp?: boolean
}

const categories: CategoryDef[] = [
  {
    id: 'length',
    name: '长度',
    base: 'm',
    units: [
      { name: '毫米', symbol: 'mm', factor: 0.001 },
      { name: '厘米', symbol: 'cm', factor: 0.01 },
      { name: '米', symbol: 'm', factor: 1 },
      { name: '千米', symbol: 'km', factor: 1000 },
      { name: '英寸', symbol: 'in', factor: 0.0254 },
      { name: '英尺', symbol: 'ft', factor: 0.3048 },
      { name: '码', symbol: 'yd', factor: 0.9144 },
      { name: '英里', symbol: 'mi', factor: 1609.344 },
      { name: '海里', symbol: 'nmi', factor: 1852 }
    ]
  },
  {
    id: 'weight',
    name: '重量',
    base: 'kg',
    units: [
      { name: '毫克', symbol: 'mg', factor: 0.000001 },
      { name: '克', symbol: 'g', factor: 0.001 },
      { name: '千克', symbol: 'kg', factor: 1 },
      { name: '吨', symbol: 't', factor: 1000 },
      { name: '盎司', symbol: 'oz', factor: 0.0283495 },
      { name: '磅', symbol: 'lb', factor: 0.453592 },
      { name: '格令', symbol: 'gr', factor: 0.00006479891 }
    ]
  },
  {
    id: 'temp',
    name: '温度',
    base: '°C',
    isTemp: true,
    units: [
      { name: '摄氏度', symbol: '°C', factor: 1 },
      { name: '华氏度', symbol: '°F', factor: 1 },
      { name: '开尔文', symbol: 'K', factor: 1 }
    ]
  },
  {
    id: 'area',
    name: '面积',
    base: 'm²',
    units: [
      { name: '平方毫米', symbol: 'mm²', factor: 0.000001 },
      { name: '平方厘米', symbol: 'cm²', factor: 0.0001 },
      { name: '平方米', symbol: 'm²', factor: 1 },
      { name: '公顷', symbol: 'ha', factor: 10000 },
      { name: '平方千米', symbol: 'km²', factor: 1000000 },
      { name: '平方英尺', symbol: 'ft²', factor: 0.092903 },
      { name: '英亩', symbol: 'acre', factor: 4046.8564224 },
      { name: '亩', symbol: '亩', factor: 666.6666667 }
    ]
  },
  {
    id: 'volume',
    name: '体积',
    base: 'L',
    units: [
      { name: '毫升', symbol: 'ml', factor: 0.001 },
      { name: '升', symbol: 'L', factor: 1 },
      { name: '立方米', symbol: 'm³', factor: 1000 },
      { name: '立方英寸', symbol: 'in³', factor: 0.0163871 },
      { name: '立方英尺', symbol: 'ft³', factor: 28.3168 },
      { name: '加仑', symbol: 'gal', factor: 3.78541 },
      { name: '品脱', symbol: 'pt', factor: 0.473176 }
    ]
  },
  {
    id: 'speed',
    name: '速度',
    base: 'm/s',
    units: [
      { name: '米/秒', symbol: 'm/s', factor: 1 },
      { name: '千米/时', symbol: 'km/h', factor: 0.277778 },
      { name: '英里/时', symbol: 'mph', factor: 0.44704 },
      { name: '节', symbol: 'kn', factor: 0.514444 },
      { name: '马赫', symbol: 'Mach', factor: 340.29 }
    ]
  },
  {
    id: 'time',
    name: '时间',
    base: 's',
    units: [
      { name: '毫秒', symbol: 'ms', factor: 0.001 },
      { name: '秒', symbol: 's', factor: 1 },
      { name: '分钟', symbol: 'min', factor: 60 },
      { name: '小时', symbol: 'h', factor: 3600 },
      { name: '天', symbol: 'd', factor: 86400 },
      { name: '周', symbol: 'w', factor: 604800 },
      { name: '月', symbol: 'mon', factor: 2629800 },
      { name: '年', symbol: 'y', factor: 31557600 }
    ]
  },
  {
    id: 'data',
    name: '数据存储',
    base: 'B',
    units: [
      { name: '比特', symbol: 'bit', factor: 0.125 },
      { name: '字节', symbol: 'B', factor: 1 },
      { name: '千字节', symbol: 'KB', factor: 1024 },
      { name: '兆字节', symbol: 'MB', factor: 1048576 },
      { name: '吉字节', symbol: 'GB', factor: 1073741824 },
      { name: '太字节', symbol: 'TB', factor: 1099511627776 },
      { name: '拍字节', symbol: 'PB', factor: 1125899906842624 }
    ]
  }
]

const currentCategoryId = ref(categories[0].id)
const currentCategory = computed(
  () => categories.find((c) => c.id === currentCategoryId.value) ?? categories[0]
)

const unitValues = reactive<Record<string, string>>({})
const unitErrors = reactive<Record<string, string>>({})

// 温度换算（基准为摄氏度）
const tempConvert: Record<string, { toC: (v: number) => number; fromC: (v: number) => number }> = {
  '°C': { toC: (v) => v, fromC: (v) => v },
  '°F': { toC: (v) => (v - 32) * (5 / 9), fromC: (v) => v * (9 / 5) + 32 },
  K: { toC: (v) => v - 273.15, fromC: (v) => v + 273.15 }
}

function formatNumber(v: number): string {
  if (!isFinite(v)) return ''
  if (v === 0) return '0'
  const abs = Math.abs(v)
  if (abs >= 1e16 || abs < 1e-6) {
    return v
      .toExponential(6)
      .replace(/(\.\d*?)0+e/, '$1e')
      .replace(/\.e/, 'e')
  }
  return parseFloat(v.toPrecision(10)).toString()
}

let unitSyncing = false

function onUnitInput(symbol: string, val: string) {
  unitValues[symbol] = val
  if (unitSyncing) return
  const cat = currentCategory.value
  const raw = val.trim()
  if (!raw) {
    unitSyncing = true
    for (const u of cat.units) {
      if (u.symbol !== symbol) {
        unitValues[u.symbol] = ''
        unitErrors[u.symbol] = ''
      }
    }
    unitSyncing = false
    return
  }
  const num = Number(raw)
  if (isNaN(num)) {
    unitErrors[symbol] = '无效输入'
    return
  }
  unitErrors[symbol] = ''
  let baseVal: number
  if (cat.isTemp) {
    baseVal = tempConvert[symbol].toC(num)
  } else {
    const u = cat.units.find((x) => x.symbol === symbol)!
    baseVal = num * u.factor
  }
  unitSyncing = true
  for (const u of cat.units) {
    if (u.symbol !== symbol) {
      const v = cat.isTemp ? tempConvert[u.symbol].fromC(baseVal) : baseVal / u.factor
      unitValues[u.symbol] = formatNumber(v)
      unitErrors[u.symbol] = ''
    }
  }
  unitSyncing = false
}

function resetCategory(cat: CategoryDef) {
  unitSyncing = true
  for (const key of Object.keys(unitValues)) delete unitValues[key]
  for (const key of Object.keys(unitErrors)) delete unitErrors[key]
  unitSyncing = false
  const first = cat.units[0]
  onUnitInput(first.symbol, '1')
}

watch(currentCategoryId, () => resetCategory(currentCategory.value), { immediate: true })
</script>

<template>
  <section class="container-page max-w-4xl py-6">
    <ToolHeader
      title="进制 / 单位换算"
      description="二 / 八 / 十 / 十六进制互转（支持大数），以及长度、重量、温度等常用单位换算。"
    />

    <el-tabs v-model="activeTab" class="mb-4">
      <el-tab-pane label="进制转换" name="base" />
      <el-tab-pane label="单位换算" name="unit" />
    </el-tabs>

    <!-- Tab 1: 进制转换 -->
    <div v-if="activeTab === 'base'" class="card p-5">
      <p class="text-xs text-text-mute mb-4">
        在任一进制中输入数字，其余进制自动同步。支持任意大整数，非法输入会在该行提示。
      </p>
      <div class="space-y-3">
        <div
          v-for="f in baseOrder"
          :key="f"
          class="flex flex-wrap items-center gap-2"
        >
          <div class="w-16 shrink-0 text-sm font-medium text-text-soft">
            {{ baseMeta[f].label }}
          </div>
          <el-input
            :model-value="baseValues[f]"
            class="flex-1 min-w-[180px] font-mono"
            :placeholder="`输入${baseMeta[f].label}数`"
            @input="(val: string | number) => onBaseInput(f, String(val))"
          >
            <template #suffix>
              <span class="text-xs text-text-mute">进制 {{ baseMeta[f].radix }}</span>
            </template>
          </el-input>
          <button
            class="btn-ghost !border !border-border whitespace-nowrap"
            title="复制"
            @click="copyText(baseValues[f])"
          >
            <el-icon><CopyDocument /></el-icon>
          </button>
          <span v-if="baseErrors[f]" class="text-xs text-danger whitespace-nowrap">
            {{ baseErrors[f] }}
          </span>
        </div>
      </div>
    </div>

    <!-- Tab 2: 单位换算 -->
    <div v-else class="space-y-4">
      <div class="card p-4 flex items-center gap-3 flex-wrap">
        <span class="text-sm text-text-soft">分类</span>
        <el-select v-model="currentCategoryId" class="w-44">
          <el-option
            v-for="c in categories"
            :key="c.id"
            :label="c.name"
            :value="c.id"
          />
        </el-select>
        <span class="text-xs text-text-mute ml-auto">
          基准单位：{{ currentCategory.base }}
        </span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div
          v-for="u in currentCategory.units"
          :key="u.symbol"
          class="card p-3"
        >
          <div class="flex items-center gap-2">
            <div class="w-20 shrink-0 text-sm text-text-soft">{{ u.name }}</div>
            <el-input
              :model-value="unitValues[u.symbol] ?? ''"
              class="flex-1 font-mono"
              @input="(val: string | number) => onUnitInput(u.symbol, String(val))"
            />
            <span class="text-xs text-text-mute w-16 shrink-0 text-right">
              {{ u.symbol }}
            </span>
          </div>
          <p v-if="unitErrors[u.symbol]" class="text-xs text-danger mt-1">
            {{ unitErrors[u.symbol] }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
</content>
</invoke>
