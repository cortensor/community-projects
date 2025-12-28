declare module 'react' {
  export interface MutableRefObject<T> { current: T }
  export interface RefObject<T> { current: T | null }
  export type Ref<T> = RefObject<T> | ((instance: T | null) => void) | null

  export function useState<T>(initial?: T): [T, (v: T) => void];
  export function useEffect(fn: () => void | (() => void), deps?: any[]): void;

  // useRef overloads: with an initial value returns a non-nullable mutable ref
  export function useRef<T>(initial: T): MutableRefObject<T>;
  export function useRef<T>(initial?: T | null): RefObject<T>;

  export const Suspense: any;
  export default any;
  export type FC<P = {}> = any;
  export type ReactNode = any;
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}
