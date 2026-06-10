import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/tauri';

export default function OnboardingWizard() {
  const [step, setStep] = useState(1);
  const [aiMode, setAiMode] = useState('cloud');
  const [apiKey, setApiKey] = useState('');
  const [localModel, setLocalModel] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [detecting, setDetecting] = useState(false);
  const [hotkey, setHotkey] = useState('Alt+Ctrl+M');
  const [hotkeyTested, setHotkeyTested] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [typedText, setTypedText] = useState('');

  const detectOllama = async () => {
    setDetecting(true);
    try {
      const models = await invoke('detect_ollama');
      setAvailableModels(models);
      if (models.length > 0) setLocalModel(models[0]);
    } catch (e) {
      alert('Could not detect Ollama. Is it running?');
    }
    setDetecting(false);
  };

  const handleHotkeyCapture = (e) => {
    e.preventDefault();
    let keys = [];
    if (e.ctrlKey) keys.push('Ctrl');
    if (e.altKey) keys.push('Alt');
    if (e.shiftKey) keys.push('Shift');
    if (e.metaKey) keys.push('Command');
    
    if (['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) return;
    
    keys.push(e.key.toUpperCase());
    setHotkey(keys.join('+'));
    setHotkeyTested(false);
  };

  const testHotkey = async () => {
    try {
      await invoke('test_hotkey', { hotkey });
      setHotkeyTested(true);
    } catch (e) {
      alert('Invalid hotkey');
    }
  };

  const launchKairo = async () => {
    const config = {
      ai_mode: aiMode,
      api_key: aiMode === 'cloud' ? apiKey : null,
      local_model: aiMode === 'local' ? localModel : null,
      hotkey: hotkey
    };
    await invoke('save_config_and_close', { config });
  };

  useEffect(() => {
    if (step === 3) {
      setIsTyping(true);
      const text = "This text is being ghost-typed directly into your application...";
      let i = 0;
      const interval = setInterval(() => {
        setTypedText(text.substring(0, i));
        i++;
        if (i > text.length) clearInterval(interval);
      }, 50);
      return () => clearInterval(interval);
    }
  }, [step]);

  return (
    <div style={{ padding: '2rem', color: '#fff', backgroundColor: '#121212', height: '100vh', fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ flex: 1, height: '4px', background: step >= 1 ? '#e94560' : '#333' }} />
        <div style={{ flex: 1, height: '4px', background: step >= 2 ? '#e94560' : '#333' }} />
        <div style={{ flex: 1, height: '4px', background: step >= 3 ? '#e94560' : '#333' }} />
      </div>

      {step === 1 && (
        <div>
          <h2>Choose your AI brain</h2>
          <div style={{ marginTop: '2rem' }}>
            <label style={{ display: 'block', padding: '1rem', border: '1px solid #333', borderRadius: '8px', marginBottom: '1rem', cursor: 'pointer', background: aiMode === 'cloud' ? '#1a1a2e' : 'transparent' }}>
              <input type="radio" checked={aiMode === 'cloud'} onChange={() => setAiMode('cloud')} />
              <strong style={{ marginLeft: '0.5rem' }}>Cloud AI (OpenAI / Anthropic / Gemini)</strong>
            </label>
            {aiMode === 'cloud' && (
              <input 
                type="password" 
                placeholder="sk-..." 
                value={apiKey} 
                onChange={(e) => setApiKey(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', background: '#1e1e1e', color: '#fff', border: '1px solid #333', borderRadius: '4px', marginBottom: '1rem' }}
              />
            )}

            <label style={{ display: 'block', padding: '1rem', border: '1px solid #333', borderRadius: '8px', cursor: 'pointer', background: aiMode === 'local' ? '#1a1a2e' : 'transparent' }}>
              <input type="radio" checked={aiMode === 'local'} onChange={() => setAiMode('local')} />
              <strong style={{ marginLeft: '0.5rem' }}>Local AI via Ollama (free, private, offline)</strong>
            </label>
            {aiMode === 'local' && (
              <div style={{ marginTop: '1rem' }}>
                <button onClick={detectOllama} disabled={detecting} style={{ padding: '0.5rem 1rem', background: '#333', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                  {detecting ? 'Detecting...' : 'Detect Ollama'}
                </button>
                {availableModels.length > 0 && (
                  <select value={localModel} onChange={(e) => setLocalModel(e.target.value)} style={{ marginLeft: '1rem', padding: '0.5rem', background: '#1e1e1e', color: '#fff', border: '1px solid #333' }}>
                    {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                )}
              </div>
            )}
          </div>
          <button 
            disabled={(aiMode === 'cloud' && !apiKey) || (aiMode === 'local' && !localModel)}
            onClick={() => setStep(2)}
            style={{ marginTop: '2rem', padding: '0.75rem 2rem', background: '#e94560', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', width: '100%' }}
          >
            Next
          </button>
        </div>
      )}

      {step === 2 && (
        <div>
          <h2>Set your hotkey</h2>
          <p style={{ color: '#aaa' }}>Press the combination you want to use to summon Kairo.</p>
          
          <input 
            type="text" 
            readOnly 
            value={hotkey}
            onKeyDown={handleHotkeyCapture}
            style={{ width: '100%', padding: '1rem', fontSize: '1.5rem', textAlign: 'center', background: '#1e1e1e', color: '#e94560', border: '2px dashed #333', borderRadius: '8px', cursor: 'pointer' }}
          />
          
          <div style={{ marginTop: '1rem', textAlign: 'center' }}>
            <button onClick={testHotkey} style={{ padding: '0.5rem 1rem', background: '#333', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Test hotkey
            </button>
            {hotkeyTested && <span style={{ marginLeft: '1rem', color: '#4ade80' }}>✓ Working!</span>}
          </div>

          <button 
            disabled={!hotkeyTested}
            onClick={() => setStep(3)}
            style={{ marginTop: '2rem', padding: '0.75rem 2rem', background: '#e94560', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', width: '100%' }}
          >
            Next
          </button>
        </div>
      )}

      {step === 3 && (
        <div>
          <h2>You're ready</h2>
          <p style={{ color: '#aaa' }}>Kairo Phantom runs quietly in the background.</p>
          
          <div style={{ marginTop: '2rem', padding: '1rem', background: '#1e1e1e', border: '1px solid #333', borderRadius: '8px', height: '150px' }}>
            <div style={{ color: '#666', marginBottom: '0.5rem' }}>Dummy Document.txt</div>
            <div style={{ color: '#fff', fontFamily: 'monospace' }}>
              {typedText}
              {isTyping && <span style={{ borderRight: '2px solid #e94560', animation: 'blink 1s step-end infinite' }}>&nbsp;</span>}
            </div>
          </div>

          <button 
            onClick={launchKairo}
            style={{ marginTop: '2rem', padding: '0.75rem 2rem', background: '#e94560', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', width: '100%', fontWeight: 'bold', fontSize: '1.1rem' }}
          >
            Launch Kairo
          </button>
        </div>
      )}
    </div>
  );
}
