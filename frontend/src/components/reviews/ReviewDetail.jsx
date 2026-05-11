import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export default function ReviewDetail({ reviewId }) {
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simular fetch
    setTimeout(() => {
      setReview({
        id: reviewId,
        product: 'Laptop Gamer Ultra',
        rating: 5,
        text: 'Excelente producto, lo recomiendo muchísimo. La batería dura todo el día y el rendimiento es increíble.',
        risk: 'Alto',
        score: 0.92,
        metadata: {
          ip: '190.12.34.56',
          device: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
          date: '2025-04-01 14:23:45',
          user_id: 'comprador123',
          previous_reviews: 0,
        },
        campaign: 'Posible campaña #12 (mismo texto repetido)'
      });
      setLoading(false);
    }, 500);
  }, [reviewId]);

  if (loading) return <div className="glass-card p-8 text-center">Cargando reseña...</div>;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 space-y-5"
    >
      <a href="/reviews" className="inline-flex items-center gap-1 text-primary hover:underline"><ArrowLeft size={18} /> Volver a la lista</a>
      <h2 className="text-2xl font-bold">Detalle de la reseña #{review.id}</h2>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <p><strong>Producto:</strong> {review.product}</p>
          <p><strong>Calificación:</strong> {review.rating}★</p>
          <p><strong>Texto completo:</strong></p>
          <div className="bg-gray-50 p-3 rounded-lg italic">"{review.text}"</div>
        </div>
        <div className="space-y-2">
          <p><strong>Riesgo IA:</strong> <Badge level={review.risk.toLowerCase()} /> (score: {review.score})</p>
          <p><strong>Campaña asociada:</strong> {review.campaign}</p>
          <div className="bg-gray-50 p-2 rounded text-xs font-mono">
            <strong>Metadatos:</strong><br />
            IP: {review.metadata.ip}<br />
            Dispositivo: {review.metadata.device.slice(0, 50)}...<br />
            Fecha: {review.metadata.date}<br />
            Usuario: {review.metadata.user_id}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 pt-4 border-t">
        <button className="btn-primary flex items-center gap-2"><CheckCircle size={18} /> Aprobar reseña</button>
        <button className="btn-danger flex items-center gap-2"><XCircle size={18} /> Eliminar (fraude)</button>
        <button className="btn-secondary flex items-center gap-2"><AlertCircle size={18} /> Marcar para revisión</button>
      </div>
    </motion.div>
  );
}

function Badge({ level }) {
  const classes = { bajo: 'badge-bajo', medio: 'badge-medio', alto: 'badge-alto' };
  return <span className={classes[level]}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>;
}