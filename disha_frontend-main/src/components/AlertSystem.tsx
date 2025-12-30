import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Volume2, VolumeX, X } from 'lucide-react';

interface AlertSystemProps {
  isInDanger: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
  distance: number | null;
  onMute: () => void;
  isMuted: boolean;
}

export default function AlertSystem({
  isInDanger,
  severity,
  distance,
  onMute,
  isMuted,
}: AlertSystemProps) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const oscillatorRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const [hasTriggered, setHasTriggered] = useState(false);

  useEffect(() => {
    if (isInDanger && !isMuted && !hasTriggered) {
      setHasTriggered(true);
      triggerBackendAlert();
      sendBrowserNotification();
    }

    if (!isInDanger) {
      setHasTriggered(false);
    }
  }, [isInDanger, isMuted, hasTriggered]);

  useEffect(() => {
    if (isInDanger && !isMuted) {
      startBuzzer();
    } else {
      stopBuzzer();
    }

    return () => {
      stopBuzzer();
    };
  }, [isInDanger, isMuted]);

  const startBuzzer = () => {
    if (oscillatorRef.current) return;

    try {
      audioContextRef.current = new (window.AudioContext || (window as never)['webkitAudioContext'])();
      const audioContext = audioContextRef.current;

      oscillatorRef.current = audioContext.createOscillator();
      gainNodeRef.current = audioContext.createGain();

      oscillatorRef.current.connect(gainNodeRef.current);
      gainNodeRef.current.connect(audioContext.destination);

      oscillatorRef.current.type = 'square';
      oscillatorRef.current.frequency.value = 800;
      gainNodeRef.current.gain.value = 0.3;

      oscillatorRef.current.start();

      let frequency = 800;
      let increasing = false;
      setInterval(() => {
        if (!oscillatorRef.current) return;
        if (increasing) {
          frequency += 50;
          if (frequency >= 1200) increasing = false;
        } else {
          frequency -= 50;
          if (frequency <= 800) increasing = true;
        }
        oscillatorRef.current.frequency.value = frequency;
      }, 100);
    } catch (error) {
      console.error('Error starting buzzer:', error);
    }
  };

  const stopBuzzer = () => {
    if (oscillatorRef.current) {
      try {
        oscillatorRef.current.stop();
        oscillatorRef.current.disconnect();
        oscillatorRef.current = null;
      } catch (error) {
        console.error('Error stopping buzzer:', error);
      }
    }

    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
        audioContextRef.current = null;
      } catch (error) {
        console.error('Error closing audio context:', error);
      }
    }
  };

  const triggerBackendAlert = async () => {
    try {
      await fetch('http://localhost:8000/api/alerts/trigger', {
        method: 'GET',
      });
    } catch (error) {
      console.error('Failed to trigger backend alert:', error);
    }
  };

  const sendBrowserNotification = async () => {
    if ('Notification' in window) {
      if (Notification.permission === 'granted') {
        new Notification('⚠️ DISHA Alert', {
          body: 'You are in a disaster threat zone! Evacuate immediately!',
          icon: '/vite.svg',
          badge: '/vite.svg',
          vibrate: [200, 100, 200],
        });
      } else if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          new Notification('⚠️ DISHA Alert', {
            body: 'You are in a disaster threat zone! Evacuate immediately!',
            icon: '/vite.svg',
            badge: '/vite.svg',
            vibrate: [200, 100, 200],
          });
        }
      }
    }
  };

  if (!isInDanger) return null;

  const severityColors = {
    low: 'bg-yellow-500',
    medium: 'bg-orange-500',
    high: 'bg-red-500',
    critical: 'bg-red-600',
  };

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 ${severityColors[severity]} text-white px-4 py-3 shadow-lg flash-animation`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <AlertTriangle className="w-6 h-6 animate-bounce" />
          <div>
            <p className="font-bold text-lg">DANGER ALERT - {severity.toUpperCase()}</p>
            <p className="text-sm">
              You are in a threat zone!
              {distance !== null && ` Distance: ${distance.toFixed(2)} km from center`}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onMute}
            className="p-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-lg transition-colors"
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
