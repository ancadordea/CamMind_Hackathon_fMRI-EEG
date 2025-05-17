import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Pause } from "lucide-react";

/*───────────────────────────────────────────────────────────────
 CamMind PinkPurple – self‑contained demo (no shadcn required)
───────────────────────────────────────────────────────────────*/

/*--------------------------------------------------------------
 Fallback UI primitives so you don’t need the shadcn generator.
 These thin wrappers keep Tailwind classes intact.
--------------------------------------------------------------*/
function Card({ className = "", children }) {
  return <div className={`rounded-2xl shadow-sm ${className}`}>{children}</div>;
}
function CardContent({ className = "", children }) {
  return <div className={className}>{children}</div>;
}
function Button({ className = "", children, ...rest }) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center font-medium focus:outline-none ${className}`}
    >
      {children}
    </button>
  );
}

// ── Sample data ───────────────────────────────────────────────
const eegMetricsSample = [
  { name: "Attention",  value: 0.72 },
  { name: "Relaxation", value: 0.55 },
  { name: "Focus",      value: 0.68 },
];

const tracks = [
  {
    title : "Nocturne No.10 Op.12",
    artist: "Bertoglio",
    cover : "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?fit=crop&w=300&q=80",
    file  : "/chopin-n10-op12-bertoglio.mp3",
  },
  {
    title : "Prelude No.4 Op.28",
    artist: "Konczal",
    cover : "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?fit=crop&w=300&q=80",
    file  : "/chopin-n4-op28-konczal.mp3",
  },
  {
    title : "Étude No.3 Op.10",
    artist: "Bertoglio",
    cover : "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?fit=crop&w=300&q=80",
    file  : "/chopin-n3-op10-bertoglio.mp3",
  },
];

/*───────────────────────────────────────────────────────────────
 Track card
───────────────────────────────────────────────────────────────*/
function TrackCard({ track, index, playingIndex, setPlayingIndex }) {
  const audioRef = useRef(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    if (playingIndex === index) a.play();
    else {
      a.pause();
      a.currentTime = 0;
      setProgress(0);
    }
  }, [playingIndex, index]);

  const handleTimeUpdate = () => {
    const a = audioRef.current;
    if (a && a.duration) setProgress((a.currentTime / a.duration) * 100);
  };

  const seek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct  = (e.clientX - rect.left) / rect.width;
    const a = audioRef.current;
    if (a && a.duration) {
      a.currentTime = pct * a.duration;
      setProgress(pct * 100);
    }
  };

  const togglePlay = () => setPlayingIndex(playingIndex === index ? null : index);

  return (
    <div className="w-52 flex-shrink-0 text-center select-none">
      <div className="relative group">
        <img src={track.cover} alt={track.title} className="w-52 h-52 object-cover rounded-xl shadow-lg" />
        <button
          onClick={togglePlay}
          className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl"
        >
          {playingIndex === index ? <Pause className="w-10 h-10 text-white" /> : <Play className="w-10 h-10 text-white" />}
        </button>
      </div>
      <p className="mt-3 text-gray-100 text-sm font-semibold line-clamp-1">{track.title}</p>
      <p className="text-xs text-gray-400 mb-2 line-clamp-1">{track.artist}</p>

      <div className="h-1.5 w-full bg-gray-700 rounded-full overflow-hidden cursor-pointer" onClick={seek}>
        <div className="h-full bg-gradient-to-r from-pink-300 via-pink-400 to-purple-500" style={{ width: `${progress}%` }} />
      </div>

      <audio ref={audioRef} src={track.file} onTimeUpdate={handleTimeUpdate} onEnded={() => setPlayingIndex(null)} />
    </div>
  );
}

/*───────────────────────────────────────────────────────────────
 Main component
───────────────────────────────────────────────────────────────*/
export default function MusicRecommenderApp() {
  const [open, setOpen] = useState(false);
  const [playingIndex, setPlayingIndex] = useState(null);

  return (
    <div className="min-h-screen bg-[#000000] text-white flex flex-col items-center p-6">
      <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-pink-300 via-pink-400 to-purple-500 text-transparent bg-clip-text">
        CamMind PinkPurple
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl mb-12">
        {eegMetricsSample.map((m) => (
          <Card key={m.name} className="bg-gray-800/80 backdrop-blur-md">
            <CardContent className="p-4 flex flex-col items-center">
              <span className="text-sm text-gray-400 uppercase tracking-wide">{m.name}</span>
              <span className="text-3xl font-semibold bg-gradient-to-r from-pink-300 via-pink-400 to-purple-500 text-transparent bg-clip-text">
                {(m.value * 100).toFixed(0)}%
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Button onClick={() => setOpen(true)} className="px-8 py-3 rounded-full bg-gradient-to-r from-pink-300 via-pink-400 to-purple-500 text-black font-semibold hover:scale-105 transition-transform shadow-xl">
        Gather recommendations
      </Button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="bg-[#0f0f0f] rounded-2xl p-8 w-[90%] max-w-5xl shadow-2xl"
            >
              <h2 className="text-2xl font-bold mb-6 bg-gradient-to-r from-pink-300 via-pink-400 to-purple-500 text-transparent bg-clip-text">
                Your personalised playlist
              </h2>

              <div className="flex flex-col sm:flex-row gap-6 justify-center mb-8 overflow-x-auto pb-2">
                {tracks.map((t, idx) => (
                  <TrackCard key={t.file} track={t} index={idx} playingIndex={playingIndex} setPlayingIndex={setPlayingIndex} />
                ))}
              </div>

              <Button onClick={() => { setOpen(false); setPlayingIndex(null); }} className="w-full bg-gradient-to-r from-pink-300 via-pink-400 to-purple-500 text-black rounded-full py-2 font-semibold">
                Close
              </Button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
