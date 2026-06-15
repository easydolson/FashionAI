# services/search_service.py
import pandas as pd
import numpy as np
import random
import faiss
from sentence_transformers import SentenceTransformer
import os
from django.conf import settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SearchService:
    def test_search(self):
        results = self.hybrid_search("джинсы", top_k=5)
        print(f"Найдено: {len(results)}")
        print(results[['name', 'price']].head())
        return results

    def __init__(self):
        # Пути к файлам (настрой в settings.py)
        self.csv_path = os.path.join(settings.BASE_DIR, 'data', 'products_dataset_first.csv')
        self.index_path = os.path.join(settings.BASE_DIR, 'data', 'faiss_index.bin')

        # Загружаем данные
        self.df = pd.read_csv(self.csv_path)
        if 'sku' not in self.df.columns:
            # Извлекаем SKU из URL
            self.df['sku'] = self.df['url'].str.extract(r'sku=(\d+)')

        # Загружаем модель
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # Загружаем FAISS-индекс
        self.index = faiss.read_index(self.index_path)

        # TF-IDF векторизатор (если нужен)

        # Подготовка TF-IDF
        corpus = self.df['summarized_caption'].fillna(self.df['description']).tolist()
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def tfidf_search(self, query, top_k=10):
        """Поиск через TF-IDF"""
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        indices = scores.argsort()[-top_k:][::-1]
        return indices, scores[indices]

    def faiss_search(self, query, top_k=10):
        """Поиск через FAISS"""
        query_emb = self.model.encode([query])
        scores, indices = self.index.search(query_emb.astype('float32'), top_k)
        return indices[0], scores[0]

    def hybrid_search(self, query, top_k=5, faiss_weight=0.4, tfidf_weight=0.6, diversify=True, lambda_param=0.6,
                      exclude_skus=None):
        """Гибридный поиск (FAISS + TF-IDF) с диверсификацией результатов"""
        # Получаем результаты
        # faiss_idx, faiss_sc = self.faiss_search(query, top_k=top_k * 3)
        # tfidf_idx, tfidf_sc = self.tfidf_search(query, top_k=top_k * 3)

        # Увеличиваем количество кандидатов, если есть исключения
        candidate_multiplier = 4 if exclude_skus else 2
        faiss_idx, faiss_sc = self.faiss_search(query, top_k=top_k * candidate_multiplier)
        tfidf_idx, tfidf_sc = self.tfidf_search(query, top_k=top_k * candidate_multiplier)

        # Получаем больше кандидатов для диверсификации
        # candidate_k = top_k * 3 if diversify else top_k

        # Нормализация FAISS
        if len(faiss_sc) > 1:
            faiss_sc_norm = (faiss_sc - faiss_sc.min()) / (faiss_sc.max() - faiss_sc.min() + 1e-8)
        else:
            faiss_sc_norm = faiss_sc

        # Нормализация TF-IDF
        if len(tfidf_sc) > 1:
            tfidf_sc_norm = (tfidf_sc - tfidf_sc.min()) / (tfidf_sc.max() - tfidf_sc.min() + 1e-8)
        else:
            tfidf_sc_norm = tfidf_sc

        # Комбинирование
        final_scores = {}
        for idx, sc in zip(faiss_idx, faiss_sc_norm):
            final_scores[idx] = final_scores.get(idx, 0) + faiss_weight * sc
        for idx, sc in zip(tfidf_idx, tfidf_sc_norm):
            final_scores[idx] = final_scores.get(idx, 0) + tfidf_weight * sc

        # Сортировка кандидатов по релевантности
        sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        candidate_indices = [idx for idx, _ in sorted_items[:top_k * 3]]  # берём больше кандидатов
        # return self.df.iloc[indices]

        # ========== ФИЛЬТРАЦИЯ ПО EXCLUDE_SKUS ==========
        if exclude_skus:
            original_count = len(candidate_indices)
            # Фильтруем индексы, исключая товары с SKU из exclude_skus
            filtered_indices = []
            for idx in candidate_indices:
                sku = self.df.iloc[idx].get('sku')
                if sku not in exclude_skus:
                    filtered_indices.append(idx)
            candidate_indices = filtered_indices
            print(f"🔍 Исключено {original_count - len(candidate_indices)} товаров, осталось {len(candidate_indices)}")

        # Если после фильтрации не осталось кандидатов — берём следующие
        if not candidate_indices:
            print("⚠️ Все кандидаты исключены, ищем дальше...")
            # Увеличиваем top_k и пробуем снова
            return self.hybrid_search(query, top_k=top_k + 5, exclude_skus=None)
        # ================================================

        # Диверсификация результатов
        if diversify and len(candidate_indices) > top_k:
            # Получаем эмбеддинги кандидатов
            candidate_embeddings = []
            for idx in candidate_indices:
                caption = self.df.iloc[idx].get('summarized_caption', '')
                if caption:
                    emb = self.model.encode([caption])[0]
                    candidate_embeddings.append(emb)
                else:
                    candidate_embeddings.append(np.zeros(384))
            candidate_embeddings = np.array(candidate_embeddings)

            # Эмбеддинг запроса
            query_emb = self.model.encode([query])[0]

            # MMR: выбираем разнообразные результаты
            selected = []
            remaining_indices = list(range(len(candidate_indices)))

            # Релевантность (косинусное сходство с запросом)
            relevance = []
            for emb in candidate_embeddings:
                sim = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-8)
                relevance.append(sim)

            for _ in range(min(top_k, len(remaining_indices))):
                best_score = -1
                best_pos = -1

                for pos in remaining_indices:
                    # Релевантность
                    rel_score = relevance[pos]

                    # Разнообразие: штраф за схожесть с уже выбранными
                    if selected:
                        sim_to_selected = max([
                            np.dot(candidate_embeddings[pos], candidate_embeddings[s]) /
                            (np.linalg.norm(candidate_embeddings[pos]) * np.linalg.norm(candidate_embeddings[s]) + 1e-8)
                            for s in selected
                        ])
                    else:
                        sim_to_selected = 0

                    # MMR score (lambda_param: 1 = только релевантность, 0 = только разнообразие)
                    mmr_score = lambda_param * rel_score - (1 - lambda_param) * sim_to_selected

                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_pos = pos

                if best_pos != -1:
                    selected.append(best_pos)
                    remaining_indices.remove(best_pos)

            # Возвращаем диверсифицированные результаты
            selected_indices = [candidate_indices[pos] for pos in selected]
            return self.df.iloc[selected_indices]

        # Без диверсификации — просто топ-k
        return self.df.iloc[candidate_indices[:top_k]]

    # def search(self, query, top_k=5):
    #     """Простой поиск через FAISS"""
    #     query_emb = self.model.encode([query])
    #     scores, indices = self.index.search(query_emb.astype('float32'), top_k)
    #     return self.df.iloc[indices[0]]

    def search(self, query, top_k=5):
        """Простой поиск через FAISS"""
        query_emb = self.model.encode([query])
        scores, indices = self.index.search(query_emb.astype('float32'), top_k)

        results = []
        for idx in indices[0]:
            row = self.df.iloc[idx]
            # Преобразуем numpy типы в Python
            price = row.get('price', 0)
            if hasattr(price, 'item'):
                price = price.item()  # numpy int → Python int

            results.append({
                'sku': str(row.get('sku', '')),
                'name': str(row.get('name', '')),
                'price': price,
                'image_filename': str(row.get('image_filename', '')),
                'url': str(row.get('url', '#')),
                'category': str(row.get('category', '')),
            })
        return results

    # search_service.py

    def get_fallback_products(self, query: str, last_category: str = None, limit: int = 5):
        """Возвращает товары для Fallback-сценария."""
        # 1. Strict Fallback (по последней категории)
        if last_category:
            results = self.df[self.df['category'].str.contains(last_category, case=False, na=False)]
            if len(results) >= limit:
                return self._to_items(results.head(limit))

        # 2. Relaxed Fallback (популярное/новое)
        # Если в вашем CSV есть колонка 'is_bestseller' или 'is_new'
        # results = self.df[self.df['is_bestseller'] == True]
        # if len(results) >= limit:
        #     return self._to_items(results.head(limit))

        # 3. Semantic Fallback (гибридный поиск по общему запросу)
        results = self.hybrid_search("популярные товары стиль", top_k=limit)
        if not results.empty:
            return self._to_items(results)

        # 4. Абсолютный Fallback (первые товары из каталога)
        return self._to_items(self.df.head(limit))

    def _to_items(self, results_df):
        """Преобразует DataFrame в список словарей для JSON."""
        items = []
        for _, row in results_df.iterrows():
            items.append({
                'sku': str(row.get('sku', '')),
                'name': row['name'],
                'price': float(row['price']),
                'image_filename': row['image_filename'],
                'url': row['url'],
                'category': row['category']
            })
        return items

    def diversify_results(self, results_df, query, model, lambda_param=0.7, top_k=5):
        """Применяет MMR для диверсификации результатов"""
        if len(results_df) <= top_k:
            return results_df

        # Получаем эмбеддинги товаров
        captions = results_df['summarized_caption'].fillna(results_df['name']).tolist()
        item_embeddings = model.encode(captions)
        query_embedding = model.encode([query])[0]

        # Нормализуем эмбеддинги
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        for i in range(len(item_embeddings)):
            item_embeddings[i] = item_embeddings[i] / np.linalg.norm(item_embeddings[i])

        # Релевантность (косинусное сходство с запросом)
        relevance = np.dot(item_embeddings, query_embedding)

        selected_indices = []
        remaining_indices = list(range(len(results_df)))

        for _ in range(min(top_k, len(remaining_indices))):
            if not selected_indices:
                # Первый товар — самый релевантный
                best_idx = remaining_indices[np.argmax(relevance[remaining_indices])]
            else:
                best_score = -1
                best_idx = -1
                for idx in remaining_indices:
                    # Релевантность
                    rel_score = relevance[idx]
                    # Сходство с уже выбранными
                    sim_to_selected = max([np.dot(item_embeddings[idx], item_embeddings[s]) for s in selected_indices])
                    # MMR score
                    mmr_score = lambda_param * rel_score - (1 - lambda_param) * sim_to_selected
                    if mmr_score > best_score:
                        best_score = mmr_score
                        best_idx = idx

            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        return results_df.iloc[selected_indices]

    # def diversify_results(self, query_embedding, candidate_indices, candidate_embeddings, lambda_param=0.5, top_k=5):
    #     """
    #     MMR diversification
    #     lambda_param = 0.5: баланс релевантности и разнообразия
    #     """
    #     selected = []
    #     remaining = list(candidate_indices)
    #
    #     # Считаем релевантность (косинусное сходство с запросом)
    #     relevance = cosine_similarity(query_embedding, candidate_embeddings)[0]
    #
    #     for _ in range(min(top_k, len(remaining))):
    #         best_score = -1
    #         best_idx = None
    #
    #         for idx in remaining:
    #             # Релевантность
    #             rel_score = relevance[idx]
    #
    #             # Разнообразие: ищем товар, максимально отличающийся от уже выбранных
    #             if selected:
    #                 sim_to_selected = max([cosine_similarity(
    #                     candidate_embeddings[idx].reshape(1, -1),
    #                     candidate_embeddings[s].reshape(1, -1)
    #                 )[0][0] for s in selected])
    #             else:
    #                 sim_to_selected = 0
    #
    #             # MMR score
    #             mmr_score = lambda_param * rel_score - (1 - lambda_param) * sim_to_selected
    #
    #             if mmr_score > best_score:
    #                 best_score = mmr_score
    #                 best_idx = idx
    #
    #         selected.append(best_idx)
    #         remaining.remove(best_idx)
    #
    #     return selected
