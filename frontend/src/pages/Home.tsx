export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">
        부동산 경매 분석 AI
      </h1>
      {/* TODO: PDF 업로드 영역 (드래그앤드롭) */}
      <p className="text-gray-500">PDF 파일을 업로드하여 분석을 시작하세요.</p>
    </div>
  )
}
