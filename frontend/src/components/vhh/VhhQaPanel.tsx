// frontend/src/components/vhh/VhhQaPanel.tsx
import React from "react";
import type { VhhQaV35 } from "@/types/vhhQa";

interface VhhQaPanelProps {
  qaV35: VhhQaV35;
}

const trafficLightColor: Record<string, string> = {
  green: "bg-green-500",
  yellow: "bg-yellow-400",
  red: "bg-red-500",
};

export const VhhQaPanel: React.FC<VhhQaPanelProps> = ({ qaV35 }) => {
  const { guideline, structural_risk_components, checks, warnings, errors, meta } =
    qaV35;

  const ranking = checks?.ranking_sanity_v3_5;
  const stability = ranking?.stability_analysis;
  const scoreConsistency = ranking?.score_consistency;

  const risk = structural_risk_components;

  return (
    <div className="w-full space-y-4">
      {/* 顶部状态条 */}
      <div className="flex items-center justify-between rounded-xl border bg-white p-4 shadow-sm">
        <div className="flex items-center space-x-3">
          <div
            className={`h-4 w-4 rounded-full ${trafficLightColor[guideline.traffic_light]}`}
          />
          <div>
            <div className="text-sm font-semibold">
              VHH QA 状态 · v{meta.version}
            </div>
            <div className="text-xs text-gray-500">
              规则集：{meta.ruleset} · {qaV35.ok ? "通过" : "未通过"}
            </div>
          </div>
        </div>
        <div className="flex space-x-2 text-xs">
          <span className="rounded-full bg-gray-100 px-2 py-1">
            总结构风险：{risk.total_risk.toFixed(2)}
          </span>
          <span className="rounded-full bg-gray-100 px-2 py-1">
            排序稳定性：{stability?.stability_score.toFixed(2)}
          </span>
          <span className="rounded-full bg-gray-100 px-2 py-1">
            Swap risk：{stability?.swap_risk.toFixed(2)}
          </span>
        </div>
      </div>

      {/* 结构风险卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <RiskCard
          title="FR2 hydrophilic patch"
          value={risk.fr2_hydrophilic_patch_risk}
          description="VHH 单域可溶性与聚集风险的关键区域。"
        />
        <RiskCard
          title="Grafting interface"
          value={risk.grafting_interface_risk}
          description="FR–CDR 界面的理化性质变化。"
        />
        <RiskCard
          title="CDR3 anchor"
          value={risk.cdr3_anchor_risk}
          description="101/102 等锚定位点匹配程度，VHH 折叠"生死线"。"
        />
        <RiskCard
          title="Total structural risk"
          value={risk.total_risk}
          description="加权合并的整体结构风险。"
        />
      </div>

      {/* Guideline 列表 */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2 rounded-xl border bg-white p-4 shadow-sm">
          <div className="mb-2 text-sm font-semibold">VHH 开发性指南</div>
          <div className="space-y-2">
            {guideline.flags.map((f) => (
              <div
                key={f.id}
                className="rounded-lg border bg-gray-50 p-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{f.id}</span>
                  <span className={levelBadgeClass(f.level)}>{f.level}</span>
                </div>
                <div className="mt-1 text-gray-600">{f.message}</div>
                <div className="mt-1 text-[10px] text-gray-400">
                  风险值：{f.value.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 排序稳定性 / Score 一致性 */}
        <div className="space-y-2 rounded-xl border bg-white p-4 shadow-sm">
          <div className="mb-2 text-sm font-semibold">排序稳定性与 Score 一致性</div>
          {stability && (
            <div className="space-y-1 text-xs">
              <div>
                排序是否稳定：
                <span className="font-semibold">
                  {stability.is_stable ? "是" : "否"}
                </span>
              </div>
              <div>稳定性评分：{stability.stability_score.toFixed(2)}</div>
              <div>Top1/Top2 Swap risk：{stability.swap_risk.toFixed(2)}</div>
              {stability.consistency_issues?.length > 0 && (
                <div className="mt-1 rounded bg-yellow-50 p-2">
                  <div className="mb-1 text-[11px] font-semibold text-yellow-700">
                    排序不一致提示：
                  </div>
                  <ul className="list-disc pl-4 text-[11px] text-yellow-800">
                    {stability.consistency_issues.map((msg, idx) => (
                      <li key={idx}>{msg}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {scoreConsistency && (
            <div className="mt-3 space-y-1 border-t pt-2 text-xs">
              <div>
                Score 一致性校准：
                <span className="font-semibold">
                  {scoreConsistency.calibrated ? "已执行" : "未执行"}
                </span>
              </div>
              {scoreConsistency.calibrated && (
                <div>
                  单调性：
                  <span className="font-semibold">
                    {scoreConsistency.is_monotonic ? "已保证" : "存在非单调"}
                  </span>
                </div>
              )}
              {scoreConsistency.reason && (
                <div className="text-[11px] text-gray-500">
                  {scoreConsistency.reason}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 错误与警告 */}
      <div className="grid gap-4 md:grid-cols-2">
        <MessageList
          title="错误（Errors）"
          items={errors}
          type="error"
          emptyText="无致命错误。"
        />
        <WarningList warnings={warnings} />
      </div>
    </div>
  );
};

interface RiskCardProps {
  title: string;
  value: number;
  description?: string;
}

const RiskCard: React.FC<RiskCardProps> = ({ title, value, description }) => {
  return (
    <div className="flex flex-col justify-between rounded-xl border bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-2 text-2xl font-bold">{value.toFixed(2)}</div>
      {description && (
        <div className="mt-1 text-xs text-gray-500">{description}</div>
      )}
    </div>
  );
};

function levelBadgeClass(level: string) {
  switch (level) {
    case "low":
      return "rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-700";
    case "medium":
      return "rounded-full bg-yellow-100 px-2 py-0.5 text-[10px] font-semibold text-yellow-700";
    case "high":
      return "rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-700";
    default:
      return "rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-gray-700";
  }
}

interface MessageListProps {
  title: string;
  items: string[];
  type: "error" | "warning";
  emptyText?: string;
}

const MessageList: React.FC<MessageListProps> = ({
  title,
  items,
  type,
  emptyText,
}) => {
  const color =
    type === "error"
      ? "border-red-200 bg-red-50 text-red-800"
      : "border-yellow-200 bg-yellow-50 text-yellow-800";

  return (
    <div className={`rounded-xl border p-4 shadow-sm ${color}`}>
      <div className="mb-2 text-sm font-semibold">{title}</div>
      {items.length === 0 ? (
        <div className="text-xs opacity-80">{emptyText}</div>
      ) : (
        <ul className="list-disc pl-4 text-xs">
          {items.map((msg, idx) => (
            <li key={idx}>{msg}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

interface WarningListProps {
  warnings: {
    level: "minor" | "major";
    category: string;
    message: string;
  }[];
}

const WarningList: React.FC<WarningListProps> = ({ warnings }) => {
  if (!warnings || warnings.length === 0) {
    return (
      <MessageList
        title="警告（Warnings）"
        type="warning"
        items={[]}
        emptyText="无重要警告。"
      />
    );
  }

  return (
    <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 text-yellow-900 shadow-sm">
      <div className="mb-2 text-sm font-semibold">警告（Warnings）</div>
      <ul className="space-y-1 text-xs">
        {warnings.map((w, idx) => (
          <li key={idx}>
            <span className="font-semibold">
              [{w.category} · {w.level}]
            </span>{" "}
            {w.message}
          </li>
        ))}
      </ul>
    </div>
  );
};

















