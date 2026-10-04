import type { ThemeRegistration } from 'shiki';

export const canaryHouseTheme: ThemeRegistration = {
  name: 'canary-house',
  type: 'light',
  colors: {
    'editor.background': '#faf8f1',
    'editor.foreground': '#20251f',
  },
  settings: [
    { scope: ['', 'source'], settings: { foreground: '#20251f' } },
    { scope: ['comment'], settings: { foreground: '#5d6670', fontStyle: 'italic' } },
    { scope: ['keyword', 'storage', 'keyword.operator'], settings: { foreground: '#2e6f63' } },
    { scope: ['string', 'string.quoted'], settings: { foreground: '#a8402e' } },
    { scope: ['constant.numeric', 'constant.language'], settings: { foreground: '#7a621a' } },
    { scope: ['entity.name', 'support.function'], settings: { foreground: '#20251f', fontStyle: 'bold' } },
    { scope: ['variable', 'meta'], settings: { foreground: '#20251f' } },
    { scope: ['punctuation'], settings: { foreground: '#5d6670' } },
  ],
};
