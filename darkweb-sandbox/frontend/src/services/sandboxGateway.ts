import { ForumThread, ListingItem } from '../types';

export interface SandboxResponse {
  html: string;
  relayPath: string;
}

export let currentRelayPath = 'Route unavailable';
type PathListener = (path: string) => void;
const pathListeners: PathListener[] = [];

export const onPathChange = (listener: PathListener) => {
  pathListeners.push(listener);
  return () => {
    const idx = pathListeners.indexOf(listener);
    if (idx > -1) pathListeners.splice(idx, 1);
  };
};

export const fetchSandboxPage = async (path: string): Promise<SandboxResponse> => {
  const url = path.startsWith('/') ? `/onion${path}` : `/onion/${path}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.statusText}`);
  }
  const html = await response.text();
  const relayPath = response.headers.get('X-Relay-Path') || 'Route unavailable';
  
  currentRelayPath = relayPath;
  pathListeners.forEach(fn => fn(relayPath));
  
  return { html, relayPath };
};

export const parseIndexPage = (html: string): { items: any[], users: string[] } => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  
  const items: any[] = [];
  const users: string[] = [];

  // Parse items
  const lists = doc.querySelectorAll('ul');
  if (lists.length > 0) {
    const itemLinks = lists[0].querySelectorAll('li');
    itemLinks.forEach((li, idx) => {
      const a = li.querySelector('a');
      if (a) {
        const textParts = li.textContent?.split('—') || li.textContent?.split('-');
        let author = 'unknown';
        let date = 'unknown';
        if (textParts && textParts.length >= 3) {
          author = textParts[1].trim();
          date = textParts[2].trim();
        }
        
        items.push({
          id: a.getAttribute('href') || `item-${idx}`,
          title: a.textContent?.trim() || 'Untitled',
          author,
          date,
          // Extract the numeric ID for internal routing
          numericId: a.getAttribute('href')?.split('/').pop() || ''
        });
      }
    });
  }

  // Parse users
  if (lists.length > 1) {
    const userLinks = lists[1].querySelectorAll('li a');
    userLinks.forEach((a) => {
      users.push(a.textContent?.trim() || '');
    });
  }

  return { items, users };
};

export const parseItemPage = (html: string) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  
  const title = doc.querySelector('h2')?.textContent || '';
  const body = doc.querySelector('.body p')?.textContent || '';
  const pgp = doc.querySelector('.pgp')?.textContent || '';
  
  const byline = doc.querySelector('.byline');
  const author = byline?.querySelector('a')?.textContent || '';
  const date = byline?.querySelector('time')?.textContent || '';

  return { title, body, pgp, author, date };
};

export const parseProfilePage = (html: string) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  
  const title = doc.querySelector('h2')?.textContent || '';
  const joined = doc.querySelector('.joined')?.textContent?.replace('Joined ', '') || '';
  const posts: any[] = [];
  
  const lists = doc.querySelectorAll('ul');
  if (lists.length > 0) {
    const itemLinks = lists[0].querySelectorAll('li');
    itemLinks.forEach((li, idx) => {
      const a = li.querySelector('a');
      if (a) {
        const date = li.querySelector('time')?.textContent || '';
        posts.push({
          id: a.getAttribute('href') || `post-${idx}`,
          title: a.textContent?.trim() || 'Untitled',
          date,
          numericId: a.getAttribute('href')?.split('/').pop() || ''
        });
      }
    });
  }

  return { title, joined, posts };
};
