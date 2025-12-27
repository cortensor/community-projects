declare module 'pdf-parse' {
  import type { TextResult } from 'pdf-parse/dist/esm/TextResult';
  type PdfParseInput = ArrayBuffer | Uint8Array | number[] | string | URL | Buffer;
  export type PdfParse = (data: PdfParseInput) => Promise<TextResult>;
  export const pdf: PdfParse;
}
