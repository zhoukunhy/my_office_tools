<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { downloadBlob } from '@/utils/file'
import ToolHeader from '@/components/tools/ToolHeader.vue'

const activeTab = ref<'gen' | 'base64' | 'hash'>('gen')

// ============ Tab1：密码生成 ============
const UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const LOWER = 'abcdefghijklmnopqrstuvwxyz'
const DIGIT = '0123456789'
const SPECIAL = '!@#$%^&*'
const SIMILAR = 'Il1O0'

const length = ref(16)
const useUpper = ref(true)
const useLower = ref(true)
const useDigit = ref(true)
const useSpecial = ref(false)
const excludeSimilar = ref(false)
const genCount = ref(5)
const passwords = ref<string[]>([])

const charset = computed(() => {
  let s = ''
  if (useUpper.value) s += UPPER
  if (useLower.value) s += LOWER
  if (useDigit.value) s += DIGIT
  if (useSpecial.value) s += SPECIAL
  if (excludeSimilar.value) {
    s = Array.from(s)
      .filter((c) => !SIMILAR.includes(c))
      .join('')
  }
  return s
})

const strength = computed(() => {
  const size = charset.value.length
  if (size === 0 || length.value === 0) {
    return { label: '无', color: '#7a8095', percent: 0, entropy: 0 }
  }
  const entropy = length.value * Math.log2(size)
  let label: string
  let color: string
  let percent: number
  if (entropy < 40) {
    label = '弱'
    color = '#ef4444'
    percent = 25
  } else if (entropy < 60) {
    label = '中'
    color = '#f59e0b'
    percent = 50
  } else if (entropy < 80) {
    label = '强'
    color = '#10b981'
    percent = 75
  } else {
    label = '极强'
    color = '#4f6eff'
    percent = 100
  }
  return { label, color, percent, entropy }
})

function randomInt(max: number): number {
  const arr = new Uint32Array(1)
  crypto.getRandomValues(arr)
  return arr[0] % max
}

function generateOne(): string {
  const cs = charset.value
  if (!cs) return ''
  let pwd = ''
  for (let i = 0; i < length.value; i++) {
    pwd += cs[randomInt(cs.length)]
  }
  return pwd
}

function generate() {
  if (!charset.value) {
    ElMessage.warning('请至少选择一种字符集')
    return
  }
  passwords.value = Array.from({ length: genCount.value }, () => generateOne())
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function copyAll() {
  if (!passwords.value.length) {
    ElMessage.warning('请先生成密码')
    return
  }
  await copyText(passwords.value.join('\n'))
}

function downloadPasswords() {
  if (!passwords.value.length) {
    ElMessage.warning('请先生成密码')
    return
  }
  const text = passwords.value.join('\n')
  downloadBlob(new Blob([text], { type: 'text/plain;charset=utf-8' }), 'passwords.txt')
  ElMessage.success('已下载')
}

// ============ Tab2：Base64 编解码 ============
const b64Input = ref('')
const b64Output = ref('')

function b64Encode() {
  if (!b64Input.value) {
    ElMessage.warning('请输入要编码的文本')
    return
  }
  try {
    // 支持 UTF-8：encodeURIComponent + btoa
    b64Output.value = btoa(
      encodeURIComponent(b64Input.value).replace(/%([0-9A-F]{2})/g, (_, p1) =>
        String.fromCharCode(parseInt(p1, 16))
      )
    )
  } catch (e) {
    ElMessage.error('编码失败：' + (e as Error).message)
  }
}

function b64Decode() {
  if (!b64Input.value) {
    ElMessage.warning('请输入要解码的文本')
    return
  }
  try {
    // 支持 UTF-8：atob + decodeURIComponent
    const binary = atob(b64Input.value.trim())
    const percent = Array.from(binary)
      .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join('')
    b64Output.value = decodeURIComponent(percent)
  } catch {
    ElMessage.error('解码失败：非合法 Base64 字符串')
  }
}

// ============ Tab3：哈希计算 ============
const hashInput = ref('')
const hashAlgo = ref<'MD5' | 'SHA1' | 'SHA256' | 'SHA512'>('SHA256')
const hashResult = ref('')
const hashing = ref(false)

const algoMap: Record<string, string> = {
  SHA1: 'SHA-1',
  SHA256: 'SHA-256',
  SHA512: 'SHA-512'
}

/** 使用 Web Crypto API 计算 SHA 哈希（返回大写十六进制） */
async function shaHash(algo: string, text: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(text)
  const hash = await crypto.subtle.digest(algo, data)
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
    .toUpperCase()
}

/**
 * 紧凑 MD5 实现（RFC 1321），纯前端、无依赖。
 * 仅用于本地校验场景，请勿用于密码存储等安全用途。
 */
function md5(input: string): string {
  const S = [
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 5, 9, 14, 20, 5,
    9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11,
    16, 23, 4, 11, 16, 23, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10,
    15, 21
  ]
  const K = [
    0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee, 0xf57c0faf, 0x4787c62a,
    0xa8304613, 0xfd469501, 0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
    0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821, 0xf61e2562, 0xc040b340,
    0x265e5a51, 0xe9b6c7aa, 0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
    0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed, 0xa9e3e905, 0xfcefa3f8,
    0x676f02d9, 0x8d2a4c8a, 0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
    0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70, 0x289b7ec6, 0xeaa127fa,
    0xd4ef3085, 0x04881d05, 0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
    0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039, 0x655b59c3, 0x8f0ccc92,
    0xffeff47d, 0x85845dd1, 0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
    0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
  ]

  const encoder = new TextEncoder()
  const bytes: number[] = Array.from(encoder.encode(input))
  const origLen = bytes.length

  // 填充：0x80 + 0x00 对齐到 56(mod 64) + 8 字节小端长度
  bytes.push(0x80)
  while (bytes.length % 64 !== 56) bytes.push(0)
  const bitLen = BigInt(origLen) * 8n
  for (let i = 0; i < 8; i++) {
    bytes.push(Number((bitLen >> BigInt(i * 8)) & 0xffn))
  }

  let a0 = 0x67452301
  let b0 = 0xefcdab89
  let c0 = 0x98badcfe
  let d0 = 0x10325476

  const roL = (x: number, c: number): number => (x << c) | (x >>> (32 - c))
  const add32 = (...args: number[]): number => {
    let sum = 0
    for (const v of args) sum = (sum + v) & 0xffffffff
    return sum >>> 0
  }

  for (let off = 0; off < bytes.length; off += 64) {
    const M: number[] = new Array(16)
    for (let i = 0; i < 16; i++) {
      M[i] =
        (bytes[off + i * 4] |
          (bytes[off + i * 4 + 1] << 8) |
          (bytes[off + i * 4 + 2] << 16) |
          (bytes[off + i * 4 + 3] << 24)) >>>
        0
    }
    let A = a0
    let B = b0
    let C = c0
    let D = d0
    for (let i = 0; i < 64; i++) {
      let F: number
      let g: number
      if (i < 16) {
        F = (B & C) | (~B & D)
        g = i
      } else if (i < 32) {
        F = (D & B) | (~D & C)
        g = (5 * i + 1) % 16
      } else if (i < 48) {
        F = B ^ C ^ D
        g = (3 * i + 5) % 16
      } else {
        F = C ^ (B | ~D)
        g = (7 * i) % 16
      }
      F = add32(A, F, K[i], M[g])
      A = D
      D = C
      C = B
      B = add32(B, roL(F, S[i]))
    }
    a0 = add32(a0, A)
    b0 = add32(b0, B)
    c0 = add32(c0, C)
    d0 = add32(d0, D)
  }

  const toHex = (n: number): string => {
    let s = ''
    for (let i = 0; i < 4; i++) {
      s += ((n >>> (i * 8)) & 0xff).toString(16).padStart(2, '0')
    }
    return s
  }
  return (toHex(a0) + toHex(b0) + toHex(c0) + toHex(d0)).toUpperCase()
}

async function computeHash() {
  if (!hashInput.value) {
    ElMessage.warning('请输入要计算哈希的文本')
    return
  }
  hashing.value = true
  try {
    if (hashAlgo.value === 'MD5') {
      hashResult.value = md5(hashInput.value)
    } else {
      hashResult.value = await shaHash(algoMap[hashAlgo.value], hashInput.value)
    }
  } catch (e) {
    ElMessage.error('计算失败：' + (e as Error).message)
  } finally {
    hashing.value = false
  }
}
</script>

<template>
  <ToolHeader
    title="密码生成 & 加密工具"
    description="生成强随机密码、Base64 编解码、哈希计算，全部本地完成，不上传任何数据。"
  />

  <div class="max-w-5xl mx-auto">
    <el-tabs v-model="activeTab" class="mb-2">
      <!-- ===== Tab 1：密码生成 ===== -->
      <el-tab-pane label="密码生成" name="gen">
        <div class="grid md:grid-cols-2 gap-6">
          <!-- 配置 -->
          <div class="card p-5 space-y-5">
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm text-text-soft">密码长度</label>
                <span class="text-sm font-mono text-primary">{{ length }}</span>
              </div>
              <el-slider v-model="length" :min="4" :max="64" :step="1" />
            </div>

            <div>
              <label class="text-sm text-text-soft block mb-2">字符集</label>
              <div class="grid grid-cols-2 gap-2">
                <el-checkbox v-model="useUpper">大写字母 (A-Z)</el-checkbox>
                <el-checkbox v-model="useLower">小写字母 (a-z)</el-checkbox>
                <el-checkbox v-model="useDigit">数字 (0-9)</el-checkbox>
                <el-checkbox v-model="useSpecial">特殊字符 (!@#$%^&amp;*)</el-checkbox>
              </div>
              <el-checkbox v-model="excludeSimilar" class="mt-2">
                排除相似字符 (Il1O0 等)
              </el-checkbox>
            </div>

            <div>
              <label class="text-sm text-text-soft block mb-2">生成数量</label>
              <el-input-number v-model="genCount" :min="1" :max="100" :step="1" />
            </div>

            <!-- 强度指示 -->
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm text-text-soft">密码强度</span>
                <span class="text-sm font-medium" :style="{ color: strength.color }">
                  {{ strength.label }}
                  <span class="text-xs text-text-mute ml-1">
                    约 {{ Math.round(strength.entropy) }} 位熵
                  </span>
                </span>
              </div>
              <div class="h-2 rounded-full bg-bg-soft overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  :style="{ width: strength.percent + '%', background: strength.color }"
                ></div>
              </div>
            </div>

            <button class="btn-primary w-full" @click="generate">
              <el-icon><MagicStick /></el-icon> 生成密码
            </button>
          </div>

          <!-- 结果 -->
          <div class="card p-5 flex flex-col">
            <div class="flex items-center justify-between mb-3">
              <h3 class="font-semibold">生成结果</h3>
              <div class="flex gap-2">
                <button
                  class="btn-ghost border border-border"
                  :disabled="!passwords.length"
                  @click="copyAll"
                >
                  <el-icon><CopyDocument /></el-icon> 全部复制
                </button>
                <button
                  class="btn-ghost border border-border"
                  :disabled="!passwords.length"
                  @click="downloadPasswords"
                >
                  <el-icon><Download /></el-icon> 下载
                </button>
              </div>
            </div>

            <div v-if="passwords.length" class="space-y-2 flex-1">
              <div
                v-for="(pwd, i) in passwords"
                :key="i"
                class="flex items-center gap-2 bg-bg-soft rounded-md px-3 py-2"
              >
                <span class="text-xs text-text-mute w-6 shrink-0">{{ i + 1 }}</span>
                <code class="font-mono text-sm flex-1 break-all">{{ pwd }}</code>
                <button class="btn-ghost !px-1.5 shrink-0" @click="copyText(pwd)">
                  <el-icon><CopyDocument /></el-icon>
                </button>
              </div>
            </div>
            <div v-else class="empty-block flex-1">
              <el-icon :size="32" class="text-text-mute mb-2"><Lock /></el-icon>
              <p class="text-sm">点击“生成密码”开始</p>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ===== Tab 2：Base64 编解码 ===== -->
      <el-tab-pane label="Base64" name="base64">
        <div class="card p-5 space-y-4">
          <div>
            <label class="text-sm text-text-soft block mb-2">输入文本</label>
            <el-input
              v-model="b64Input"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 10 }"
              placeholder="输入要编码 / 解码的文本"
            />
          </div>
          <div class="flex flex-wrap gap-2">
            <button class="btn-primary" @click="b64Encode">
              <el-icon><Upload /></el-icon> 编码 (Encode)
            </button>
            <button class="btn-primary" @click="b64Decode">
              <el-icon><Download /></el-icon> 解码 (Decode)
            </button>
          </div>
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="text-sm text-text-soft">结果</label>
              <button class="btn-ghost" :disabled="!b64Output" @click="copyText(b64Output)">
                <el-icon><CopyDocument /></el-icon> 复制结果
              </button>
            </div>
            <el-input
              v-model="b64Output"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 10 }"
              readonly
              placeholder="结果将显示在此处"
            />
          </div>
          <p class="text-xs text-text-mute">
            支持 UTF-8 中文编码，编码与解码均在本地浏览器完成。
          </p>
        </div>
      </el-tab-pane>

      <!-- ===== Tab 3：哈希计算 ===== -->
      <el-tab-pane label="哈希计算" name="hash">
        <div class="card p-5 space-y-4">
          <div>
            <label class="text-sm text-text-soft block mb-2">输入文本</label>
            <el-input
              v-model="hashInput"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 10 }"
              placeholder="输入要计算哈希的文本"
            />
          </div>
          <div class="flex flex-col sm:flex-row gap-3 sm:items-end">
            <div class="flex-1">
              <label class="text-sm text-text-soft block mb-2">算法</label>
              <el-select v-model="hashAlgo" class="w-full">
                <el-option label="MD5" value="MD5" />
                <el-option label="SHA-1" value="SHA1" />
                <el-option label="SHA-256" value="SHA256" />
                <el-option label="SHA-512" value="SHA512" />
              </el-select>
            </div>
            <button class="btn-primary" :disabled="hashing" @click="computeHash">
              <el-icon v-if="hashing" class="animate-spin"><Loading /></el-icon>
              <el-icon v-else><MagicStick /></el-icon>
              {{ hashing ? '计算中…' : '计算哈希' }}
            </button>
          </div>
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="text-sm text-text-soft">哈希结果（大写十六进制）</label>
              <button class="btn-ghost" :disabled="!hashResult" @click="copyText(hashResult)">
                <el-icon><CopyDocument /></el-icon> 复制
              </button>
            </div>
            <el-input
              v-model="hashResult"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 8 }"
              readonly
              class="font-mono"
              placeholder="哈希值将显示在此处"
            />
          </div>
          <p class="text-xs text-text-mute">
            SHA 系列使用 Web Crypto API (crypto.subtle.digest) 计算；MD5 为内置纯 JS 实现，仅用于本地校验，请勿用于密码存储等安全场景。
          </p>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
