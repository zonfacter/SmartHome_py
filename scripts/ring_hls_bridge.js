#!/usr/bin/env node
/*
 * Ring -> HLS bridge process.
 * Uses an existing refresh token (no new login) and writes an HLS playlist/segments.
 */

const { RingApi } = require('ring-client-api')

function getArg(name) {
  const idx = process.argv.indexOf(`--${name}`)
  if (idx === -1) return null
  return process.argv[idx + 1] || null
}

const refreshToken = process.env.RING_REFRESH_TOKEN || getArg('refresh-token')
const cameraId = getArg('camera-id')
const playlist = getArg('playlist')
const segmentPattern = getArg('segment-pattern')
const ffmpegPath = getArg('ffmpeg') || 'ffmpeg'

if (!refreshToken || !cameraId || !playlist || !segmentPattern) {
  console.error('Missing required args: --refresh-token --camera-id --playlist --segment-pattern')
  process.exit(2)
}

let ringApi = null
let liveCall = null
let stopping = false

async function cleanupAndExit(code = 0) {
  if (stopping) return
  stopping = true
  try {
    if (liveCall) {
      liveCall.stop()
      liveCall = null
    }
  } catch (_) {}
  try {
    if (ringApi) {
      ringApi.disconnect()
      ringApi = null
    }
  } catch (_) {}
  process.exit(code)
}

process.on('SIGTERM', () => cleanupAndExit(0))
process.on('SIGINT', () => cleanupAndExit(0))
process.on('uncaughtException', (e) => {
  console.error('ring bridge uncaughtException', e?.message || e)
  cleanupAndExit(1)
})
process.on('unhandledRejection', (e) => {
  console.error('ring bridge unhandledRejection', e?.message || e)
  cleanupAndExit(1)
})

;(async () => {
  ringApi = new RingApi({
    refreshToken,
    ffmpegPath,
    debug: false,
  })

  const cameras = await ringApi.getCameras()
  const cam = cameras.find((c) => String(c.id) === String(cameraId))
  if (!cam) {
    throw new Error(`Ring camera not found: ${cameraId}`)
  }

  liveCall = await cam.streamVideo({
    input: [
      '-fflags', 'nobuffer',
      '-flags', 'low_delay',
      '-probesize', '32768',
      '-analyzeduration', '0',
      '-reorder_queue_size', '0',
    ],
    audio: ['-an'],
    video: ['-vcodec', 'copy'],
    output: [
      '-f', 'hls',
      '-hls_time', '0.6',
      '-hls_list_size', '6',
      '-hls_delete_threshold', '10',
      '-hls_flags', 'delete_segments+append_list+omit_endlist+independent_segments+split_by_time',
      '-muxdelay', '0',
      '-muxpreload', '0',
      '-hls_segment_filename', segmentPattern,
      playlist,
    ],
  })

  // Keep process alive until external stop.
  setInterval(() => {
    if (!stopping) {
      process.stdout.write('')
    }
  }, 15000)
})().catch((e) => {
  console.error('ring bridge start failed', e?.message || e)
  cleanupAndExit(1)
})
