import { injectable } from 'inversify';
import { IHttpClient, HttpResponse } from '../interfaces';

@injectable()
export class HttpClient implements IHttpClient {
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || '';
  }

  async get<T = any>(url: string, config?: RequestInit): Promise<HttpResponse<T>> {
    return this.request<T>(url, { ...config, method: 'GET' });
  }

  async post<T = any>(url: string, data?: any, config?: RequestInit): Promise<HttpResponse<T>> {
    return this.request<T>(url, {
      ...config,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...config?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T = any>(url: string, data?: any, config?: RequestInit): Promise<HttpResponse<T>> {
    return this.request<T>(url, {
      ...config,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...config?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async del<T = any>(url: string, config?: RequestInit): Promise<HttpResponse<T>> {
    return this.request<T>(url, { ...config, method: 'DELETE' });
  }

  private async request<T = any>(url: string, config: RequestInit): Promise<HttpResponse<T>> {
    const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;
    
    const response = await fetch(fullUrl, {
      ...config,
      headers: {
        'Accept': 'application/json',
        ...config.headers,
      },
    });

    const responseHeaders: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });

    let data: T;
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = (await response.text()) as unknown as T;
    }

    const result: HttpResponse<T> = {
      data,
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    };

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
    }

    return result;
  }
}