import { useState } from 'react';
import { Eye, Filter } from 'lucide-react';
import { motion } from 'framer-motion';

const mockReviews = [
  { id: 1, product: 'Laptop Gamer', rating: 5, text: 'Excelente producto, lo recomiendo muchísimo', risk: 'Alto', date: '2025-04-01', user: 'comp123' },
  { id: 2, product: 'Auriculares Bluetooth', rating: 1, text: 'Malisimo, no funciona', risk: 'Bajo', date: '2025-04-02', user: 'user456' },
  { id: 3, product: 'Smartwatch Pro', rating: 5, text: 'Me encanta, es perfecto, nunca falla', risk: 'Medio', date: '2025-04-03', user: 'buyer789' },
  { id: 4, product: 'Cafetera Express', rating: 5, text: 'Excelente producto, lo recomiendo muchísimo', risk: 'Alto', date: '2025-04-01', user: 'coffeeLover' },
];

export default function ReviewsTable() {
  const [filter, setFilter] = useState('Todos');
  const filtered = filter === 'Todos' ? mockReviews : mockReviews.filter(r => r.risk === filter);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass-card p-4 overflow-x-auto"
    >
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <div className="flex gap-2">
          {['Todos', 'Bajo', 'Medio', 'Alto'].map(level => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={`px-3 py-1 rounded-full text-sm transition ${filter === level ? 'bg-primary text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              {level}
            </button>
          ))}
        </div>
        <div className="flex gap-1 text-sm text-gray-500"><Filter size={16} /> Filtrar por riesgo</div>
      </div>

      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="text-left py-2 px-2">Producto</th><th>Calif.</th><th>Texto</th><th>Riesgo</th><th>Usuario</th><th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((review, index) => (
            <motion.tr
              key={review.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className="border-b hover:bg-gray-50 transition"
            >
              <td className="py-2 px-2 font-medium">{review.product}</td>
              <td className="text-center">{review.rating}★</td>
              <td className="max-w-xs truncate">{review.text}</td>
              <td><Badge level={review.risk.toLowerCase()} /></td>
              <td className="text-gray-500">{review.user}</td>
              <td>
                <a href={`/reviews/${review.id}`} className="text-primary hover:underline flex items-center gap-1">
                  <Eye size={16} /> Ver
                </a>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
}

function Badge({ level }) {
  const classes = { bajo: 'badge-bajo', medio: 'badge-medio', alto: 'badge-alto' };
  return <span className={classes[level]}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>;
}