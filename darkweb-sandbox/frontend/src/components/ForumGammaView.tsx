import React, { useState, useEffect } from 'react';
import { ShieldAlert, Terminal, Activity, Play, Pause, RefreshCw, Cpu, Server } from 'lucide-react';
import { RELAYS_POOL } from '../data/mockData';
import { ForumThread } from '../types';
import { fetchSandboxPage, parseIndexPage, parseItemPage } from '../services/sandboxGateway';

export const ForumGammaView: React.FC = () => {
  const [isStreaming, setIsStreaming] = useState(true);
  const [threads, setThreads] = useState<ForumThread[]>([]);
  const [selectedThread, setSelectedThread] = useState<ForumThread | null>(null);

  const [logs, setLogs] = useState<string[]>([
    '[03:14:02] INITIALIZING CIRCUIT TRACE ON ONION 0x44F99A',
    '[03:14:05] GUARD RELAY HANDSHAKE: relay-06 (Iceland, 89.234.157.254)',
    '[03:14:09] CELL RELAY_EXTEND SENT -> MIDDLE RELAY relay-01 (Germany)',
    '[03:14:12] CELL RELAY_EXTENDED RECEIVED. DIFFIE-HELLMAN KEY DERIVED',
    '[03:14:15] EXIT RELAY NEGOTIATION: relay-07 (Sweden, 185.241.208.204)',
    '[03:14:18] RENDEZVOUS COOKIE MATCHED: 0x98A1_STEALTH_SESSION_OPEN',
    '[03:14:22] PACKET TIMING CORRELATION COEFFICIENT: 0.982 (HIGH CONFIDENCE)'
  ]);

  useEffect(() => {
    const loadThreads = async () => {
      try {
        const { html } = await fetchSandboxPage('gamma2xd6bt5hy.onion.mock/');
        const { items } = parseIndexPage(html);
        const mappedThreads: ForumThread[] = items.map((item: any) => ({
          id: item.numericId,
          title: item.title,
          tag: 'RESEARCH',
          tagColor: 'text-emerald-300 bg-emerald-950/80 border-emerald-500/30',
          author: item.author,
          replies: 0,
          views: 0,
          timeAgo: item.date,
          excerpt: '',
          content: [],
          rawHref: item.id
        }));
        setThreads(mappedThreads);
      } catch (err) {
        console.error("Error loading Gamma threads", err);
      }
    };
    loadThreads();
  }, []);

  const handleSelectThread = async (thread: ForumThread) => {
    if (selectedThread?.id === thread.id) {
      setSelectedThread(null);
      return;
    }
    setSelectedThread(thread);
    try {
      const href = (thread as any).rawHref;
      const { html } = await fetchSandboxPage(href.startsWith('/') ? href.substring(1) : href);
      const { body, pgp } = parseItemPage(html);
      setSelectedThread({
        ...thread,
        content: pgp ? [body, pgp] : [body]
      });
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (!isStreaming) return;
    const interval = setInterval(() => {
      const randomRelay = RELAYS_POOL[Math.floor(Math.random() * RELAYS_POOL.length)];
      const cellTypes = ['RELAY_DATA', 'RELAY_SENDME', 'PADDING_NEGOTIATE', 'INTRO_ESTABLISHED', 'CIRCUIT_PURGE'];
      const randomCell = cellTypes[Math.floor(Math.random() * cellTypes.length)];
      const timestamp = new Date().toTimeString().split(' ')[0];
      const newEntry = `[${timestamp}] ${randomCell} via ${randomRelay.name} (${randomRelay.country}) - ${Math.floor(Math.random() * 512 + 128)} bytes`;

      setLogs((prev) => [...prev.slice(-14), newEntry]);
    }, 2400);

    return () => clearInterval(interval);
  }, [isStreaming]);

  return (
    <div id="view-forum-gamma" className="p-4 md:p-6 space-y-5 max-w-6xl mx-auto font-mono text-gray-200">
      {/* Title */}
      <div className="border-b border-[#153634] pb-4 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-[#2bf0a6]" />
            <h2 className="text-xl font-bold text-[#2bf0a6] tracking-wide">
              Forum Gamma :: Deep Research &amp; Operations
            </h2>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Restricted research sandbox enclave. De-anonymization telemetry &amp; circuit correlation monitors.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsStreaming(!isStreaming)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[#0d1f20] hover:bg-[#112929] border border-[#1d4a46] text-xs text-[#2bf0a6] cursor-pointer"
          >
            {isStreaming ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isStreaming ? 'Pause Telemetry' : 'Resume Telemetry'}</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="p-3.5 bg-[#0d1f20] border border-[#153634] rounded space-y-1">
          <div className="flex items-center justify-between text-gray-400">
            <span>Threat Correlation Score</span>
            <Activity className="w-4 h-4 text-[#2bf0a6]" />
          </div>
          <div className="text-2xl font-bold text-[#2bf0a6]">98.2%</div>
          <p className="text-[10px] text-gray-500">Bayesian timing pattern match</p>
        </div>

        <div className="p-3.5 bg-[#0d1f20] border border-[#153634] rounded space-y-1">
          <div className="flex items-center justify-between text-gray-400">
            <span>Circuit Hop Latency</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400">142 ms</div>
          <p className="text-[10px] text-gray-500">Guard: relay-06 • Exit: relay-07</p>
        </div>

        <div className="p-3.5 bg-[#0d1f20] border border-[#153634] rounded space-y-1">
          <div className="flex items-center justify-between text-gray-400">
            <span>Enclave Security Level</span>
            <Server className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">ISOLATED</div>
          <p className="text-[10px] text-gray-500">No outbound LAN leakage</p>
        </div>
      </div>

      {/* Terminal Telemetry Display */}
      <div className="bg-[#050c0d] border border-[#1d4a46] rounded-lg p-4 font-mono shadow-2xl space-y-3">
        <div className="flex items-center justify-between border-b border-[#153634] pb-2 text-xs">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-[#2bf0a6]" />
            <span className="font-bold text-gray-200">INTERCEPTED CELL TELEMETRY LOG</span>
          </div>
          <span className="text-[10px] text-[#1da876] bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2bf0a6] animate-pulse" />
            LIVE PROBE
          </span>
        </div>

        <div className="h-64 overflow-y-auto space-y-1 text-xs text-gray-300 font-mono bg-black/50 p-3 rounded border border-[#153634]/60">
          {logs.map((line, idx) => (
            <div
              key={idx}
              className={`${
                line.includes('HIGH CONFIDENCE')
                  ? 'text-[#2bf0a6] font-bold'
                  : line.includes('INITIALIZING')
                  ? 'text-cyan-300'
                  : 'text-gray-400'
              }`}
            >
              {line}
            </div>
          ))}
        </div>

        <div className="text-[10px] text-gray-500 pt-1 flex items-center justify-between">
          <span>Target Onion Service: marketplace-beta.onion.mock</span>
          <span>Protocol: v3 Stealth Authorization</span>
        </div>
      </div>

      {/* Actual Sandbox Data */}
      <div className="bg-[#0a1617] border border-[#1d4a46] rounded-lg p-4 font-mono shadow-2xl space-y-3">
        <div className="text-xs font-bold text-[#2bf0a6] border-b border-[#153634] pb-2">
          CAPTURED FORUM GAMMA THREADS
        </div>
        <div className="space-y-2">
          {threads.length === 0 ? (
             <div className="text-xs text-gray-400">Loading captured threads...</div>
          ) : threads.map((thread) => (
            <div key={thread.id} className="p-2.5 bg-[#0d1f20] border border-[#153634] rounded text-xs space-y-1 hover:border-[#2bf0a6]/50 transition cursor-pointer" onClick={() => handleSelectThread(thread)}>
              <div className="flex justify-between text-[#2bf0a6] font-semibold">
                <span>{thread.title}</span>
                <span className="text-[10px] text-gray-500">{thread.timeAgo}</span>
              </div>
              <div className="text-[10px] text-gray-400">Author: {thread.author}</div>
              {selectedThread?.id === thread.id && (
                <div className="mt-2 p-2 bg-[#061113] border border-[#153634] text-gray-300 whitespace-pre-wrap">
                  {selectedThread.content.join('\n\n')}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
