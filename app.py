import streamlit as st
import pandas as pd
import numpy as np
import re
from collections import Counter
import jieba
import io
import requests
from snownlp import SnowNLP
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import base64
import tempfile

# 设置页面配置
st.set_page_config(
    page_title="语言分析工具",
    page_icon="📚",
    layout="wide"
)

# 导航栏
st.sidebar.title('导航栏')
page = st.sidebar.radio(
    '选择页面',
    ['首页', 'B站弹幕分析', '语料清洗', '语言分析']
)

# 首页
if page == '首页':
    st.title('欢迎使用语言分析工具')
    st.write("""
    本工具提供以下功能：
    - B站弹幕分析：支持B站视频弹幕获取和分析
    - 语料清洗：提供多种文本预处理选项
    - 语言分析：包含词频统计、字符统计等分析功能
    
    请使用左侧导航栏选择所需功能。
    """)
    
    # 展示一些示例或使用说明
    with st.expander("使用说明"):
        st.write("""
        1. 所有功能都支持文件导入导出
        2. 支持的文件格式：TXT, CSV, XLSX
        3. 建议单次处理文本大小不超过10MB
        """)

# B站弹幕分析部分
elif page == 'B站弹幕分析':
    st.title('B站弹幕分析')
    
    # 输入B站视频URL
    video_url = st.text_input('请输入B站视频URL:')
    
    if video_url:
        try:
            # 获取视频信息
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.bilibili.com'
            }
            
            response = requests.get(video_url, headers=headers)
            response.raise_for_status()
            
            # 获取cid
            cid_match = re.search(r'"cid":(\d+)', response.text)
            if not cid_match:
                st.error("无法在页面中找到cid")
            else:
                cid = cid_match.group(1)
                
                # 获取弹幕数据
                danmaku_url = f'https://api.bilibili.com/x/v1/dm/list.so?oid={cid}'
                response = requests.get(danmaku_url, headers=headers)
                content = response.content.decode('utf-8')
                
                pattern = r'<d p="([0-9.]+),.*?">(.*?)</d>'
                matches = re.findall(pattern, content)
                
                if not matches:
                    st.warning("未找到弹幕")
                else:
                    danmaku_list = []
                    for time_str, text in matches:
                        seconds = float(time_str)
                        minutes = int(seconds // 60)
                        remaining_seconds = int(seconds % 60)
                        formatted_time = f"{minutes:02d}:{remaining_seconds:02d}"
                        
                        danmaku_list.append({
                            'time': formatted_time,
                            'time_seconds': seconds,
                            'text': text.strip()
                        })
                    
                    # 按时间排序
                    danmaku_list.sort(key=lambda x: x['time_seconds'])
                    
                    # 显示弹幕数据
                    st.write(f"共获取到 {len(danmaku_list)} 条弹幕")
                    
                    # 分析选项
                    analysis_options = st.multiselect(
                        '选择分析类型',
                        ['词频统计', '情感分析', '词云图', '时间分布']
                    )
                    
                    if analysis_options:
                        texts = [item['text'] for item in danmaku_list]
                        
                        if '词频统计' in analysis_options:
                            # 分词统计
                            words = []
                            for text in texts:
                                words.extend(jieba.cut(text))
                            
                            # 过滤停用词
                            stop_words = {'的', '了', '是', '啊', '吧', '吗', '在', '和', '就', '都', '这', '有', '我', '你', '他'}
                            words = [w for w in words if w not in stop_words and len(w) > 1]
                            
                            word_freq = Counter(words).most_common(20)
                            freq_df = pd.DataFrame(word_freq, columns=['词语', '频次'])
                            st.write('词频统计结果:')
                            st.dataframe(freq_df)
                        
                        if '情感分析' in analysis_options:
                            sentiments = []
                            for text in texts:
                                try:
                                    sentiment = SnowNLP(text).sentiments
                                    sentiments.append(sentiment)
                                except:
                                    continue
                            
                            sentiment_dist = {
                                '积极': len([s for s in sentiments if s > 0.6]),
                                '中性': len([s for s in sentiments if 0.4 <= s <= 0.6]),
                                '消极': len([s for s in sentiments if s < 0.4])
                            }
                            
                            st.write('情感分析结果:')
                            sentiment_df = pd.DataFrame([sentiment_dist])
                            st.dataframe(sentiment_df)
                        
                        if '词云图' in analysis_options:
                            # 生成词云
                            word_freq_dict = dict(Counter(words).most_common(100))
                            wc = WordCloud(
                                width=800,
                                height=400,
                                background_color='white',
                                font_path='SimHei.ttf'
                            ).generate_from_frequencies(word_freq_dict)
                            
                            fig, ax = plt.subplots(figsize=(10, 5))
                            ax.imshow(wc, interpolation='bilinear')
                            ax.axis('off')
                            st.pyplot(fig)
                        
                        if '时间分布' in analysis_options:
                            times = [item['time_seconds'] for item in danmaku_list]
                            fig, ax = plt.subplots(figsize=(10, 5))
                            ax.hist(times, bins=20)
                            ax.set_xlabel('视频时间(秒)')
                            ax.set_ylabel('弹幕数量')
                            st.pyplot(fig)
                    
                    # 导出选项
                    export_format = st.selectbox(
                        '选择导出格式',
                        ['CSV', 'Excel']
                    )
                    
                    if export_format == 'CSV':
                        df = pd.DataFrame(danmaku_list)
                        csv = df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name="danmaku.csv",
                            mime="text/csv"
                        )
                    else:
                        df = pd.DataFrame(danmaku_list)
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                            df.to_excel(tmp.name, index=False)
                            with open(tmp.name, 'rb') as f:
                                excel_data = f.read()
                            st.download_button(
                                label="下载Excel文件",
                                data=excel_data,
                                file_name="danmaku.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
        except Exception as e:
            st.error(f"获取弹幕失败: {str(e)}")

# 语料清洗部分
elif page == '语料清洗':
    st.title('语料清洗')
    
    # 文件上传
    uploaded_file = st.file_uploader("上传需要清洗的文件", type=['txt', 'csv'])
    
    if uploaded_file is not None:
        text_to_clean = uploaded_file.read().decode()
    else:
        text_to_clean = st.text_area('或直接输入需要清洗的文本:', height=200)
    
    if text_to_clean:
        # 清洗选项
        col1, col2 = st.columns(2)
        with col1:
            remove_punct = st.checkbox('删除标点符号')
            remove_numbers = st.checkbox('删除数字')
        with col2:
            to_lowercase = st.checkbox('转换为小写')
            remove_spaces = st.checkbox('删除多余空格')
        
        if st.button('开始清洗'):
            # 执行清洗
            if remove_punct:
                text_to_clean = re.sub(r'[^\w\s]', '', text_to_clean)
            if remove_numbers:
                text_to_clean = re.sub(r'\d+', '', text_to_clean)
            if to_lowercase:
                text_to_clean = text_to_clean.lower()
            if remove_spaces:
                text_to_clean = ' '.join(text_to_clean.split())
            
            st.write('清洗后的文本:')
            st.text_area('结果', text_to_clean, height=200)
            
            # 导出功能
            buf = io.BytesIO()
            buf.write(text_to_clean.encode())
            st.download_button(
                label="下载清洗后的文本",
                data=buf.getvalue(),
                file_name="cleaned_text.txt",
                mime="text/plain"
            )

# 语言分析部分
else:
    st.title('语言分析')
    
    # 文件上传
    uploaded_file = st.file_uploader("上传要分析的文件", type=['txt', 'csv'])
    
    if uploaded_file is not None:
        analysis_text = uploaded_file.read().decode()
    else:
        analysis_text = st.text_area('或直接输入要分析的文本:', height=200)
    
    if analysis_text:
        # 分析选项
        analysis_type = st.multiselect(
            '选择分析类型',
            ['词频统计', '字符统计', '词云图']
        )
        
        if '词频统计' in analysis_type:
            words = jieba.lcut(analysis_text)
            word_freq = Counter(words)
            freq_df = pd.DataFrame.from_dict(word_freq, orient='index', columns=['频次'])
            freq_df = freq_df.sort_values('频次', ascending=False)
            
            st.write('词频统计结果:')
            st.dataframe(freq_df)
            
            # 导出词频统计结果
            csv = freq_df.to_csv().encode()
            st.download_button(
                label="下载词频统计结果",
                data=csv,
                file_name="word_frequency.csv",
                mime="text/csv"
            )
        
        if '字符统计' in analysis_type:
            char_count = len(analysis_text)
            word_count = len(analysis_text.split())
            
            st.write(f'字符数: {char_count}')
            st.write(f'词数: {word_count}')
            
            # 导出统计结果
            stats_dict = {'字符数': char_count, '词数': word_count}
            stats_df = pd.DataFrame([stats_dict])
            csv = stats_df.to_csv().encode()
            st.download_button(
                label="下载统计结果",
                data=csv,
                file_name="text_statistics.csv",
                mime="text/csv"
            )
        if '词云图' in analysis_type:
            # 生成词云图
            words = jieba.lcut(analysis_text)
            word_freq = Counter(words)
            
            # 使用安全的词云生成函数
            try:
                wc = WordCloud(
                    width=800,
                    height=400,
                    background_color='white',
                    max_words=200,
                    max_font_size=100,
                    random_state=42,
                    font_path='SimHei.ttf'
                ).generate_from_frequencies(word_freq)
                
                # 将词云图转换为图片
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wc, interpolation='bilinear')
                ax.axis('off')
                plt.tight_layout(pad=0)
                
                # 在Streamlit中显示词云图
                st.pyplot(fig)
                
                # 提供下载词云图的选项
                img = io.BytesIO()
                plt.savefig(img, format='PNG')
                img.seek(0)
                
                st.download_button(
                    label="下载词云图",
                    data=img,
                    file_name="wordcloud.png",
                    mime="image/png"
                )
                plt.close()
            except Exception as e:
                st.error(f"生成词云图失败: {str(e)}")
