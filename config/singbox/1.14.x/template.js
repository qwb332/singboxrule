// Sub-Store Template Script for Sing-Box
log(`🚀 开始`)

let { type, name, outbound, includeUnsupportedProxy, url } = $arguments

log(`传入参数 type: ${type}, name: ${name}, outbound: ${outbound}`)

type = /^1$|col|组合/i.test(type) ? 'collection' : 'subscription'

const parser = ProxyUtils.JSON5 || JSON
log(`① 使用 ${ProxyUtils.JSON5 ? 'JSON5' : 'JSON'} 解析配置文件`)
let config
try {
  config = parser.parse($content ?? $files[0])
} catch (e) {
  log(`${e.message ?? e}`)
  throw new Error(`配置文件不是合法的 ${ProxyUtils.JSON5 ? 'JSON5' : 'JSON'} 格式`)
}
log(`② 获取订阅`)

let proxies = []
let outbounds = []
let endpoints = []
let data = {}
if (url) {
  log(`直接从 URL ${url} 读取订阅`)
  data = await produceArtifact({
    name,
    type,
    platform: 'sing-box',
    produceOpts: {
      'include-unsupported-proxy': includeUnsupportedProxy,
    },
    subscription: {
      name,
      url,
      source: 'remote',
    },
  })
} else {
  log(`将读取名称为 ${name} 的 ${type === 'collection' ? '组合' : ''}订阅`)
  data = await produceArtifact({
    name,
    type,
    platform: 'sing-box',
    produceOpts: {
      'include-unsupported-proxy': includeUnsupportedProxy,
    },
  })
}
data = JSON.parse(data)
outbounds = data.outbounds ?? []
endpoints = data.endpoints ?? []

// WireGuard 自动转换为 Endpoint
let wgEndpoints = [];
outbounds = outbounds.filter(ob => {
  if (ob.type === 'wireguard') {
    const peer = {
      address: ob.server,
      port: ob.server_port,
      public_key: ob.peer_public_key,
      allowed_ips: ["0.0.0.0/0", "::/0"]
    };
    if (ob.reserved) peer.reserved = ob.reserved;
    if (ob.pre_shared_key) peer.pre_shared_key = ob.pre_shared_key;

    const endpoint = {
      type: 'wireguard',
      tag: ob.tag,
      private_key: ob.private_key,
      peers: [peer]
    };

    if (ob.local_address) endpoint.address = ob.local_address;
    if (ob.mtu) endpoint.mtu = ob.mtu;

    wgEndpoints.push(endpoint);
    log(`🛡️ 成功将 WireGuard 节点 [${ob.tag}] 转换为 1.11+ 标准 Endpoint 格式`);
    return false;
  }
  return true;
});

endpoints.push(...wgEndpoints);

proxies = [...outbounds, ...endpoints]

log(`获取到 ${outbounds.length} 个节点, ${endpoints.length} 个端点`)

log(`③ outbound 规则解析`)
const outboundRules = outbound
  .split('🕳')
  .map(i => i.trim())
  .filter(i => i)
  .map(i => {
    let [outboundPattern, tagPattern = '.*'] = i.split('🏷')
    const tagRegex = createTagRegExp(tagPattern)
    log(`匹配 🏷 ${tagRegex} 的节点将插入匹配 🕳 ${createOutboundRegExp(outboundPattern)} 的 outbound 中`)
    return [outboundPattern, tagRegex]
  })

log(`④ outbound 插入节点`)
if (!Array.isArray(config.outbounds)) {
  config.outbounds = []
}
config.outbounds.map(outbound => {
  outboundRules.map(([outboundPattern, tagRegex]) => {
    const outboundRegex = createOutboundRegExp(outboundPattern)
    if (outboundRegex.test(outbound.tag)) {
      if (!Array.isArray(outbound.outbounds)) {
        outbound.outbounds = []
      }
      const tags = getTags(proxies, tagRegex)
      log(`🕳 ${outbound.tag} 匹配 ${outboundRegex}, 插入 ${tags.length} 个 🏷 匹配 ${tagRegex} 的节点`)
      outbound.outbounds.push(...tags)
    }
  })
})

const compatible_outbound = {
  tag: 'COMPATIBLE',
  type: 'direct',
}

let compatible
log(`⑤ 空 outbounds 检查`)
config.outbounds.map(outbound => {
  outboundRules.map(([outboundPattern, tagRegex]) => {
    const outboundRegex = createOutboundRegExp(outboundPattern)
    if (outboundRegex.test(outbound.tag)) {
      if (!Array.isArray(outbound.outbounds)) {
        outbound.outbounds = []
      }
      if (outbound.outbounds.length === 0) {
        if (!compatible) {
          config.outbounds.push(compatible_outbound)
          compatible = true
        }
        log(`🕳 ${outbound.tag} 的 outbounds 为空, 自动插入 COMPATIBLE(direct)`)
        outbound.outbounds.push(compatible_outbound.tag)
      }
    }
  })
})

config.outbounds.push(...outbounds)
if (!Array.isArray(config.endpoints)) {
  config.endpoints = []
}
config.endpoints.push(...endpoints)

// sing-box Hysteria 2 兼容格式洗白
if (Array.isArray(config.outbounds)) {
  config.outbounds = config.outbounds.map(outbound => {
    if (outbound.type === 'hysteria2') {
      if (!outbound.tls) outbound.tls = {};
      outbound.tls.insecure = true;

      delete outbound.obfs;
      delete outbound.obfs_type;
      delete outbound.obfs_password;
      delete outbound["obfs-type"];
      delete outbound["obfs-password"];

      log(`🛡️ 成功将 Hysteria 2 [${outbound.tag}] 洗白为官方文档标准格式`);
    }
    return outbound;
  });
}

$content = JSON.stringify(config, null, 2)

function getTags(proxies, regex) {
  return (regex ? proxies.filter(p => regex.test(p.tag)) : proxies).map(p => p.tag)
}
function log(v) {
  console.log(`[📦 sing-box 模板脚本] ${v}`)
}
function createTagRegExp(tagPattern) {
  return new RegExp(tagPattern.replace('ℹ️', ''), tagPattern.includes('ℹ️') ? 'i' : undefined)
}
function createOutboundRegExp(outboundPattern) {
  return new RegExp(outboundPattern.replace('ℹ️', ''), outboundPattern.includes('ℹ️') ? 'i' : undefined)
}

log(`🔚 结束`)
