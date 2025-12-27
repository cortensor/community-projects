'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Loader2, Newspaper, Rocket, Network, Shuffle } from 'lucide-react';

interface NewsItem {
  title: string;
  url: string;
  source: string;
  publishedAt?: string;
  description?: string;
  category?: string;
}

type Category = 'general' | 'technology' | 'science' | 'random';

const categories: { id: Category; label: string; icon: React.ElementType }[] = [
  { id: 'general', label: 'Top News', icon: Newspaper },
  { id: 'technology', label: 'Technology', icon: Rocket },
  { id: 'science', label: 'Science', icon: Network },
  { id: 'random', label: 'Random Article', icon: Shuffle }
];

export function NewsPanel({ className }: { className?: string }) {
  const [activeCategory, setActiveCategory] = useState<Category>('general');
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNews = async (category: Category) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/news?category=${category}&t=${Date.now()}`);
      if (!res.ok) throw new Error('Gagal memuat berita');
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNews(activeCategory);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCategory]);

  return (
    <Card className={className}>
      <CardHeader className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Newspaper className="h-5 w-5" />
              <span>News & Articles</span>
            </CardTitle>
            <CardDescription>
              Quick curation for research ideas and fresh trends.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => loadNews(activeCategory)} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          {categories.map((cat) => (
            <Button
              key={cat.id}
              variant={activeCategory === cat.id ? 'default' : 'outline'}
              size="sm"
              className="justify-start"
              onClick={() => setActiveCategory(cat.id)}
            >
              <cat.icon className="h-4 w-4 mr-2" />
              {cat.label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mb-2" />
            Loading…
          </div>
        ) : error ? (
          <div className="text-sm text-destructive">{error}</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-muted-foreground">No data.</div>
        ) : (
          <div className="space-y-3 max-h-[28rem] overflow-y-auto pr-1">
            {items.map((item, idx) => (
              <div key={`${item.url}-${idx}`} className="p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-semibold text-sm leading-snug hover:underline"
                    >
                      {item.title}
                    </a>
                    {item.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">{item.description}</p>
                    )}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Badge variant="outline" className="text-[10px]">{String(item.source)}</Badge>
                      {item.publishedAt && <span>{new Date(item.publishedAt).toLocaleDateString()}</span>}
                      {item.category && <span>{item.category}</span>}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            <Separator className="my-1" />
            <p className="text-[11px] text-muted-foreground">
              Sources: NewsAPI / GNews / Mediastack / HN / Dev.to / Reddit / NASA / arXiv / Wikipedia.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
