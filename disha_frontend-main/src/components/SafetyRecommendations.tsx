import { useState } from 'react';
import { Lightbulb, Volume2, VolumeX, ChevronDown, ChevronUp } from 'lucide-react';
import { mockSafetyRecommendations } from '../data/mockData';

interface SafetyRecommendationsProps {
  disasterType: string;
  isInDanger: boolean;
}

export default function SafetyRecommendations({
  disasterType,
  isInDanger,
}: SafetyRecommendationsProps) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['Immediate Actions'])
  );

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const handleVoiceReadout = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const text = mockSafetyRecommendations
      .map((rec) => {
        const items = rec.items.join('. ');
        return `${rec.category}. ${items}`;
      })
      .join('. ');

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1;
    utterance.volume = 1;

    utterance.onend = () => {
      setIsSpeaking(false);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
    };

    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-4 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          <h3 className="font-bold text-lg text-gray-800">Safety Tips</h3>
        </div>
        <button
          onClick={handleVoiceReadout}
          className={`p-2 ${
            isSpeaking ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'
          } rounded-lg hover:opacity-80 transition-colors`}
          title={isSpeaking ? 'Stop' : 'Read aloud'}
        >
          {isSpeaking ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>
      </div>

      <div
        className={`mb-4 p-3 rounded-lg ${
          isInDanger ? 'bg-red-50 border-2 border-red-500' : 'bg-blue-50 border-2 border-blue-500'
        }`}
      >
        <p className="font-semibold text-gray-800">
          {disasterType} - {isInDanger ? 'Active Threat' : 'Monitoring'}
        </p>
        <p className="text-sm text-gray-600 mt-1">
          {isInDanger
            ? 'Follow these recommendations immediately'
            : 'Review these guidelines for preparedness'}
        </p>
      </div>

      <div className="space-y-3">
        {mockSafetyRecommendations.map((recommendation) => {
          const isExpanded = expandedCategories.has(recommendation.category);
          return (
            <div
              key={recommendation.category}
              className="border border-gray-200 rounded-lg overflow-hidden"
            >
              <button
                onClick={() => toggleCategory(recommendation.category)}
                className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <span className="font-semibold text-gray-800">{recommendation.category}</span>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-gray-600" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-600" />
                )}
              </button>
              {isExpanded && (
                <div className="p-3 bg-white">
                  <ul className="space-y-2">
                    {recommendation.items.map((item, idx) => (
                      <li key={idx} className="flex items-start space-x-2 text-sm text-gray-700">
                        <span className="text-blue-600 font-bold mt-0.5">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {isInDanger && (
        <div className="mt-4 p-3 bg-orange-50 border-2 border-orange-500 rounded-lg">
          <p className="text-sm font-semibold text-orange-800">
            ⚠️ Remember: Your safety is the top priority. Follow official instructions and evacuate
            if advised.
          </p>
        </div>
      )}
    </div>
  );
}
