import { useState } from 'react'

interface PropertyInfoCardProps {
  caseNumber: string | null
  address: string | null
  propertyType: string | null
  debtorName: string | null
  creditorName: string | null
}

function InfoItem({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-xs text-gray-500 shrink-0">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  )
}

function CopyIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={className ?? 'w-3.5 h-3.5'}>
      <path d="M7 3.5A1.5 1.5 0 0 1 8.5 2h3.879a1.5 1.5 0 0 1 1.06.44l3.122 3.12A1.5 1.5 0 0 1 17 6.622V12.5a1.5 1.5 0 0 1-1.5 1.5h-1v-3.379a3 3 0 0 0-.879-2.121L10.5 5.379A3 3 0 0 0 8.379 4.5H7v-1Z" />
      <path d="M4.5 6A1.5 1.5 0 0 0 3 7.5v9A1.5 1.5 0 0 0 4.5 18h7a1.5 1.5 0 0 0 1.5-1.5v-5.879a1.5 1.5 0 0 0-.44-1.06L9.44 6.439A1.5 1.5 0 0 0 8.378 6H4.5Z" />
    </svg>
  )
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={className ?? 'w-3.5 h-3.5'}>
      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z" clipRule="evenodd" />
    </svg>
  )
}

function AddressItem({ address }: { address: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(address)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-start gap-2 sm:col-span-2 lg:col-span-3">
      <span className="text-xs text-gray-500 shrink-0 mt-0.5">소재지</span>
      <span className="text-sm font-medium text-gray-900 break-words">{address}</span>
      <button
        onClick={handleCopy}
        title={copied ? '복사됨' : '주소 복사'}
        className="shrink-0 mt-0.5 text-gray-400 hover:text-gray-600 transition-colors"
      >
        {copied ? (
          <CheckIcon className="w-3.5 h-3.5 text-green-500" />
        ) : (
          <CopyIcon />
        )}
      </button>
    </div>
  )
}

export default function PropertyInfoCard({
  caseNumber,
  address,
  propertyType,
  debtorName,
  creditorName,
}: PropertyInfoCardProps) {
  const hasAny = caseNumber || address || propertyType || debtorName || creditorName
  if (!hasAny) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <InfoItem label="사건번호" value={caseNumber} />
        <InfoItem label="물건종류" value={propertyType} />
        <InfoItem label="채무자" value={debtorName} />
        <InfoItem label="채권자" value={creditorName} />
        {address && <AddressItem address={address} />}
      </div>
    </div>
  )
}
