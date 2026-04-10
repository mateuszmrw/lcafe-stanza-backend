export interface LanguageInfo {
  name: string
  flag: string
}

export const LANGUAGE_FLAGS: Record<string, LanguageInfo> = {
  BG: { name: "Bulgarian", flag: "🇧🇬" },
  CS: { name: "Czech", flag: "🇨🇿" },
  DA: { name: "Danish", flag: "🇩🇰" },
  DE: { name: "German", flag: "🇩🇪" },
  EL: { name: "Greek", flag: "🇬🇷" },
  EN: { name: "English", flag: "🇬🇧" },
  ES: { name: "Spanish", flag: "🇪🇸" },
  ET: { name: "Estonian", flag: "🇪🇪" },
  FI: { name: "Finnish", flag: "🇫🇮" },
  FR: { name: "French", flag: "🇫🇷" },
  HU: { name: "Hungarian", flag: "🇭🇺" },
  ID: { name: "Indonesian", flag: "🇮🇩" },
  IT: { name: "Italian", flag: "🇮🇹" },
  JA: { name: "Japanese", flag: "🇯🇵" },
  KO: { name: "Korean", flag: "🇰🇷" },
  LT: { name: "Lithuanian", flag: "🇱🇹" },
  LV: { name: "Latvian", flag: "🇱🇻" },
  NB: { name: "Norwegian", flag: "🇳🇴" },
  NL: { name: "Dutch", flag: "🇳🇱" },
  PL: { name: "Polish", flag: "🇵🇱" },
  PT: { name: "Portuguese", flag: "🇵🇹" },
  RO: { name: "Romanian", flag: "🇷🇴" },
  RU: { name: "Russian", flag: "🇷🇺" },
  SK: { name: "Slovak", flag: "🇸🇰" },
  SL: { name: "Slovenian", flag: "🇸🇮" },
  SV: { name: "Swedish", flag: "🇸🇪" },
  TR: { name: "Turkish", flag: "🇹🇷" },
  UK: { name: "Ukrainian", flag: "🇺🇦" },
  ZH: { name: "Chinese", flag: "🇨🇳" },
}

export function getLanguageLabel(code: string): string {
  const info = LANGUAGE_FLAGS[code.toUpperCase()]
  return info ? `${info.flag} ${info.name}` : code
}
