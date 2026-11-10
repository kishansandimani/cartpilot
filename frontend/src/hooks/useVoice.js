import { useCallback, useEffect, useRef, useState } from 'react'

const SR = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null
export const LOCALES = { en: 'en-IN', hi: 'hi-IN', kn: 'kn-IN' }
const BARS = 20

/**
 * Browser voice: speech-to-text (Web Speech API), live waveform (Web Audio), and speech output.
 * status: idle | listening | processing | success | error
 * NOTE: Chrome/Edge send audio to a speech service, so this needs internet. It is NOT offline voice.
 */
export function useVoice({ lang = 'en', onFinal }) {
  const [status, setStatus] = useState('idle')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')
  const [levels, setLevels] = useState(() => Array(BARS).fill(0))
  const recRef = useRef(null)
  const streamRef = useRef(null)
  const rafRef = useRef(0)
  const ctxRef = useRef(null)
  const finalRef = useRef('')
  const erroredRef = useRef(false)
  const onFinalRef = useRef(onFinal)
  onFinalRef.current = onFinal
  const supported = !!SR

  const cleanupAudio = useCallback(() => {
    cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    ctxRef.current?.close().catch(() => {})
    ctxRef.current = null
    setLevels(Array(BARS).fill(0))
  }, [])

  const stop = useCallback(() => { recRef.current?.stop() }, [])

  const start = useCallback(async () => {
    setError(''); setTranscript(''); finalRef.current = ''; erroredRef.current = false
    if (!SR) { setStatus('error'); setError('Voice recognition is not supported in this browser. Use Chrome or Edge, or type your command.'); return }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      ctxRef.current = ctx
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 64
      ctx.createMediaStreamSource(stream).connect(analyser)
      const data = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(data)
        setLevels(Array.from({ length: BARS }, (_, i) => data[i % data.length] / 255))
        rafRef.current = requestAnimationFrame(tick)
      }
      tick()
    } catch (e) {
      cleanupAudio(); setStatus('error')
      setError(e?.name === 'NotAllowedError' || e?.name === 'SecurityError'
        ? 'Microphone permission was denied. Click the lock icon in the address bar, allow the microphone for this site, then try again.'
        : e?.name === 'NotFoundError' ? 'No microphone was found on this device.' : 'Could not access the microphone.')
      return
    }
    const rec = new SR()
    rec.lang = LOCALES[lang] || 'en-IN'
    rec.interimResults = true
    rec.continuous = false
    rec.onresult = (ev) => {
      let interim = ''
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const t = ev.results[i][0].transcript
        if (ev.results[i].isFinal) finalRef.current += t
        else interim += t
      }
      setTranscript((finalRef.current + ' ' + interim).trim())
    }
    rec.onerror = (ev) => {
      erroredRef.current = true
      cleanupAudio(); setStatus('error')
      setError(ev.error === 'not-allowed' ? 'Microphone permission was denied. Allow microphone access for this site and try again.'
        : ev.error === 'no-speech' ? 'I did not hear anything. Please try again.'
        : ev.error === 'language-not-supported' ? 'This browser does not support speech recognition for the selected language. Type your command instead.'
        : ev.error === 'network' ? 'Speech recognition needs an internet connection.' : `Voice error: ${ev.error}`)
    }
    rec.onend = () => {
      cleanupAudio()
      if (erroredRef.current) return // onerror already showed the message
      const text = finalRef.current.trim()
      if (text) { setStatus('processing'); onFinalRef.current?.(text) } else setStatus('idle')
    }
    recRef.current = rec
    setStatus('listening')
    rec.start()
  }, [lang, cleanupAudio])

  useEffect(() => () => { recRef.current?.abort(); cleanupAudio(); window.speechSynthesis?.cancel() }, [cleanupAudio])

  const speak = useCallback((text, l = lang) => {
    if (!('speechSynthesis' in window) || !text) return false
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = LOCALES[l] || 'en-IN'
    window.speechSynthesis.speak(u)
    return true
  }, [lang])

  return { supported, status, setStatus, transcript, setTranscript, error, setError, levels, start, stop, speak }
}
