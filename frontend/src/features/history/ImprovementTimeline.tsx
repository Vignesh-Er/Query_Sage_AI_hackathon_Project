import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { Card } from "../../design-system/components/Card";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";
import { Award } from "lucide-react";

interface TimelinePoint {
  submitted_at: string;
  query_score: number;
  rolling_average: number;
}

interface ImprovementTimelineProps {
  data: TimelinePoint[];
}

export const ImprovementTimeline: React.FC<ImprovementTimelineProps> = ({ data }) => {
  const getLatestPoints = () => {
    if (data.length === 0) return { score: 100, avg: 100, delta: 0 };
    const latest = data[data.length - 1];
    const prev = data[Math.max(0, data.length - 2)];
    return {
      score: latest.query_score,
      avg: latest.rolling_average,
      delta: latest.query_score - prev.query_score
    };
  };

  const stats = getLatestPoints();

  // Format date for chart labels
  const chartData = data.map((pt) => ({
    ...pt,
    dateStr: new Date(pt.submitted_at).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    })
  }));

  return (
    <Card className="p-4 border-border bg-pitch" style={{ fontFamily: TOKENS.fonts.ui }}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-textPrimary flex items-center gap-1.5">
            <Award size={16} className="text-ember" />
            <span>Scorecard Evolution Timeline</span>
          </h3>
          <p className="text-[10px] text-textSecondary mt-0.5">
            Tracking your database optimization and code efficiency metrics over time
          </p>
        </div>
        
        <div className="flex items-center gap-4 text-xs font-code">
          <div className="text-right">
            <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-ui">
              Current score
            </span>
            <span className="font-bold text-sm text-ember">{stats.score.toFixed(1)}</span>
          </div>
          <div className="text-right">
            <span className="block text-[9px] uppercase tracking-wider text-textSecondary font-ui">
              Rolling average
            </span>
            <span className="font-bold text-sm text-glacier">{stats.avg.toFixed(1)}</span>
          </div>
        </div>
      </div>

      <div className="h-[200px] w-full text-[10px]">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
              <defs>
                <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={TOKENS.colors.ember} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={TOKENS.colors.ember} stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorAvg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={TOKENS.colors.glacier} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={TOKENS.colors.glacier} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E3356" opacity={0.3} />
              <XAxis dataKey="dateStr" stroke="#3D5166" />
              <YAxis domain={[0, 100]} stroke="#3D5166" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: TOKENS.colors.pitch, 
                  borderColor: TOKENS.colors.border,
                  color: TOKENS.colors.text.primary,
                  fontFamily: TOKENS.fonts.ui,
                  fontSize: "10px"
                }} 
              />
              <Legend verticalAlign="top" height={32} iconSize={8} />
              <Area
                name="Query Score"
                type="monotone"
                dataKey="query_score"
                stroke={TOKENS.colors.ember}
                fillOpacity={1}
                fill="url(#colorScore)"
                strokeWidth={2}
              />
              <Area
                name="Rolling Average"
                type="monotone"
                dataKey="rolling_average"
                stroke={TOKENS.colors.glacier}
                fillOpacity={1}
                fill="url(#colorAvg)"
                strokeWidth={1.5}
                strokeDasharray="4 4"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center h-full border border-dashed border-border/50 text-textSecondary text-[11px]">
            <span>No scorecard history entries recorded.</span>
            <span>Profile SQL queries to generate database optimization charts.</span>
          </div>
        )}
      </div>
    </Card>
  );
};
