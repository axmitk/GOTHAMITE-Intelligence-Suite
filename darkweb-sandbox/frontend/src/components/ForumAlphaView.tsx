import React, { useState, useEffect } from 'react';
import { MessageSquare, Eye, Clock, User, ShieldAlert, Check, Plus, Search } from 'lucide-react';
import { ForumThread } from '../types';
import { fetchSandboxPage, parseIndexPage, parseItemPage } from '../services/sandboxGateway';

export const ForumAlphaView: React.FC = () => {
  const [threads, setThreads] = useState<ForumThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<ForumThread | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [replyText, setReplyText] = useState('');
  const [replySuccess, setReplySuccess] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadThreads = async () => {
      try {
        const { html } = await fetchSandboxPage('alpha7fq2mx9k.onion.mock/');
        const { items } = parseIndexPage(html);
        
        const mappedThreads: ForumThread[] = items.map((item: any, idx: number) => ({
          id: item.numericId,
          title: item.title,
          tag: 'INTEL', // default visual tag
          tagColor: 'text-amber-300 bg-amber-950/80 border-amber-500/30',
          author: item.author,
          replies: 0,
          views: 0,
          timeAgo: item.date,
          excerpt: 'Click to load thread content...',
          content: [],
          rawHref: item.id
        }));
        
        setThreads(mappedThreads);
      } catch (err) {
        console.error("Error loading Forum Alpha:", err);
      } finally {
        setLoading(false);
      }
    };
    loadThreads();
  }, []);

  const handleSelectThread = async (thread: ForumThread) => {
    setSelectedThread(thread);
    try {
      const href = (thread as any).rawHref;
      const { html } = await fetchSandboxPage(href.startsWith('/') ? href.substring(1) : href);
      const { body, pgp } = parseItemPage(html);
      
      const content = [body];
      if (pgp) content.push(pgp);
      
      setSelectedThread({
        ...thread,
        excerpt: body.substring(0, 150) + '...',
        content
      });
    } catch (err) {
      console.error("Error loading thread details", err);
    }
  };

  const filteredThreads = threads.filter((t) => {
    const matchesFilter = activeFilter === 'ALL' || t.tag === activeFilter;
    const matchesSearch =
      !searchQuery ||
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.excerpt.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.author.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleAddReply = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !selectedThread) return;

    setReplySuccess(true);
    setTimeout(() => {
      setSelectedThread({
        ...selectedThread,
        replies: selectedThread.replies + 1,
        content: [...selectedThread.content, `[Reply by sandbox_analyst]: ${replyText.trim()}`]
      });
      setReplyText('');
      setReplySuccess(false);
    }, 600);
  };

  return (
    <div id="view-forum-alpha" className="p-4 md:p-6 space-y-4 max-w-6xl mx-auto font-mono text-gray-200">
      {/* Top Banner */}
      <div className="border-b border-[#153634] pb-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <MessageSquare className="w-5 h-5 text-[#2bf0a6]" />
            <h2 className="text-xl font-bold text-[#2bf0a6] tracking-wide">
              Forum Alpha :: Discussions &amp; Leaks
            </h2>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Simulated underground discussions, CVE analysis, and threat actor telemetry feeds.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs bg-[#0d1f20] px-3 py-1.5 rounded border border-[#153634] text-gray-300">
            Active Threads: {threads.length}
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap gap-1.5">
          {['ALL', '0-DAY', 'INTEL', 'TUTORIAL', 'RESEARCH'].map((tag) => (
            <button
              key={tag}
              onClick={() => setActiveFilter(tag)}
              className={`px-3 py-1 rounded border transition cursor-pointer ${
                activeFilter === tag
                  ? 'bg-[#112929] text-[#2bf0a6] border-[#2bf0a6]/50 font-semibold'
                  : 'bg-[#0d1f20] text-gray-400 border-[#153634] hover:text-white'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Filter threads..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#040c0d] border border-[#1d4a46] rounded pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-[#2bf0a6]"
          />
        </div>
      </div>

      {/* Thread Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Thread List (Left 2/3) */}
        <div className={`${selectedThread ? 'lg:col-span-1' : 'lg:col-span-3'} space-y-2.5`}>
          {filteredThreads.map((thread) => {
            const isSelected = selectedThread?.id === thread.id;
            return (
              <div
                key={thread.id}
                onClick={() => handleSelectThread(thread)}
                className={`p-3.5 bg-[#0d1f20] border rounded cursor-pointer transition shadow-xs ${
                  isSelected
                    ? 'border-[#2bf0a6] bg-[#112929]/90'
                    : 'border-[#153634] hover:border-[#2bf0a6]/50'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    className={`text-xs md:text-sm font-semibold hover:text-[#2bf0a6] transition ${
                      isSelected ? 'text-[#2bf0a6]' : 'text-gray-200'
                    }`}
                  >
                    {thread.title}
                  </span>
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-bold shrink-0 ${thread.tagColor}`}
                  >
                    {thread.tag}
                  </span>
                </div>

                <p className="text-[11px] text-gray-400 mt-1 line-clamp-2">{thread.excerpt}</p>

                <div className="flex items-center justify-between text-[10px] text-gray-500 mt-2.5 pt-2 border-t border-[#153634]/60">
                  <div className="flex items-center space-x-1.5">
                    <User className="w-3 h-3 text-[#2bf0a6]" />
                    <span className="text-[#2bf0a6]">{thread.author}</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3 h-3" /> {thread.replies}
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="w-3 h-3" /> {thread.views}
                    </span>
                    <span>{thread.timeAgo}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Thread Reading Pane */}
        {selectedThread && (
          <div className="lg:col-span-2 bg-[#0a1617] border border-[#1d4a46] rounded-lg p-5 space-y-4 shadow-xl">
            <div className="flex items-start justify-between border-b border-[#153634] pb-3">
              <div>
                <span
                  className={`text-[9px] px-2 py-0.5 rounded border uppercase font-bold ${selectedThread.tagColor}`}
                >
                  {selectedThread.tag}
                </span>
                <h3 className="text-base font-bold text-white mt-1.5">{selectedThread.title}</h3>
                <div className="text-[11px] text-gray-400 mt-1 flex items-center space-x-3">
                  <span>Author: <span className="text-[#2bf0a6]">@{selectedThread.author}</span></span>
                  <span>•</span>
                  <span>Posted: {selectedThread.timeAgo}</span>
                  <span>•</span>
                  <span>{selectedThread.views} Reads</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedThread(null)}
                className="text-xs text-gray-400 hover:text-white px-2 py-1 bg-[#0d1f20] rounded border border-[#153634]"
              >
                Close Pane
              </button>
            </div>

            <div className="space-y-2.5 text-xs text-gray-300">
              <div className="text-[11px] text-[#2bf0a6] font-semibold uppercase tracking-wider">
                Intelligence Disclosure / Whitepaper
              </div>
              <p className="text-gray-300 leading-relaxed bg-[#061113] p-3 rounded border border-[#153634]/70">
                {selectedThread.excerpt}
              </p>

              <div className="space-y-2 pt-2">
                <div className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">
                  Thread Transcript &amp; Analysis
                </div>
                {selectedThread.content.map((paragraph, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-[#0d1f20] border border-[#153634] rounded text-[11px] text-gray-300 leading-relaxed"
                  >
                    {paragraph}
                  </div>
                ))}
              </div>
            </div>

            {/* Reply Form */}
            <form onSubmit={handleAddReply} className="pt-3 border-t border-[#153634] space-y-2">
              <div className="text-[11px] text-gray-400 font-semibold">Post Encrypted Response (Sandbox)</div>
              <textarea
                rows={2}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder="Write signed commentary or threat mitigation note..."
                className="w-full bg-[#040c0d] border border-[#1d4a46] rounded p-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-[#2bf0a6]"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={!replyText.trim()}
                  className="px-4 py-1.5 bg-[#2bf0a6] hover:bg-emerald-400 text-black font-bold text-xs rounded transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Submit Comment</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
