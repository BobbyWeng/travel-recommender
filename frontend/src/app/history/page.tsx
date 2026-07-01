import SearchHistory from "@/components/SearchHistory";

export default function HistoryPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <h1 className="text-xl font-bold text-gray-900 mb-6">搜索历史</h1>
      <SearchHistory />
    </div>
  );
}
