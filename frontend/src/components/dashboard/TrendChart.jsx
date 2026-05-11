import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';

const trend = [
  { date: 'Lun', fraud: 3 },
  { date: 'Mar', fraud: 5 },
  { date: 'Mié', fraud: 2 },
  { date: 'Jue', fraud: 8 },
  { date: 'Vie', fraud: 12 },
  { date: 'Sáb', fraud: 7 },
  { date: 'Dom', fraud: 4 },
];

export default function TrendChart() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="glass-card p-4"
    >
      <h3 className="font-semibold text-lg mb-2">Reseñas fraudulentas (última semana)</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={trend}>
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="fraud" stroke="#EF4444" strokeWidth={2} dot={{ r: 4, fill: '#EF4444' }} />
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
}