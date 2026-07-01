"use client";

interface LLMExplanationProps {
  explanation: string;
}

export default function LLMExplanation({ explanation }: LLMExplanationProps) {
  if (!explanation) return null;

  return (
    <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-xl p-5">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
          <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-purple-800 mb-2">
            AI 推荐解读
          </h3>
          <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
            {explanation}
          </div>
        </div>
      </div>
    </div>
  );
}
