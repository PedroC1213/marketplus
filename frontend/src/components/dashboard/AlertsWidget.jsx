import { AlertTriangle, Clock } from 'lucide-react';
import { motion } from 'framer-motion';

const alerts = [
  { id: 1, product: 'Smartphone X', risk: 'Alto', reason: 'Pico de 20 reseñas 5★ en 30 minutos', time: 'Hace 2h' },
  { id: 2, product: 'Cafetera Ultra', risk: 'Medio', reason: 'Lenguaje repetitivo en 8 reseñas', time: 'Hace 5h' },
  { id: 3, product: 'Auriculares Pro', risk: 'Alto', reason: 'Mismo texto copiado 12 veces', time: 'Ayer' },
];

export default function AlertsWidget() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="glass-card p-4"
    >
      <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-warning" /> Alertas activas
      </h3>
      <ul className="divide-y divide-gray-200">
        {alerts.map((alert) => (
          <li key={alert.id} className="py-3 flex justify-between items-center">
            <div>
              <p className="font-medium">{alert.product}</p>
              <p className="text-sm text-gray-600">{alert.reason}</p>
              <p className="text-xs text-gray-400 flex items-center gap-1 mt-1"><Clock size={12} /> {alert.time}</p>
            </div>
            <Badge level={alert.risk.toLowerCase()} />
          </li>
        ))}
      </ul>
      <a href="/campaigns" className="text-primary text-sm block mt-3 text-center hover:underline">Ver todas las campañas →</a>
    </motion.div>
  );
}

// Badge helper (puedes importar desde ui/Badge, pero aquí lo definimos rápido)
function Badge({ level }) {
  const classes = {
    bajo: 'badge-bajo',
    medio: 'badge-medio',
    alto: 'badge-alto'
  };
  return <span className={classes[level]}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>;
}