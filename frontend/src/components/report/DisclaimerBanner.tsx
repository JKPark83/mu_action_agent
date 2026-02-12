const DEFAULT_TEXT =
  '본 분석 결과는 AI에 의한 참고용 정보이며, 최종 투자 판단의 책임은 사용자에게 있습니다. 법률, 세무 등 전문 영역은 반드시 전문가의 자문을 받으시기 바랍니다.'

export default function DisclaimerBanner({ text }: { text?: string }) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
      <svg className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
      <p className="text-sm text-amber-800 leading-relaxed">{text || DEFAULT_TEXT}</p>
    </div>
  )
}
