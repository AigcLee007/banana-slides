import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowUp, Home, Image, Key, Languages, Save } from 'lucide-react';
import { Button, Card, Input, Loading, useToast } from '@/components/shared';
import * as api from '@/api/endpoints';
import type { Settings as SettingsType } from '@/types';

type OutputLanguage = SettingsType['output_language'];

const FIXED_SETTINGS = {
  ai_provider_format: 'gemini',
  api_base_url: 'https://vip.aittco.com',
  text_model: 'gemini-3-flash-preview',
  image_model: 'gemini-3-pro-image-preview',
  image_caption_model: 'gemini-3-flash-preview',
  text_model_source: 'gemini',
  image_model_source: 'gemini',
  image_caption_model_source: 'gemini',
} as const;

const languageLabels: Record<OutputLanguage, string> = {
  zh: '中文',
  en: 'English',
  ja: '日本語',
  auto: '自动',
};

const initialFormData = {
  api_key: '',
  image_resolution: '2K',
  image_aspect_ratio: '16:9',
  output_language: 'zh' as OutputLanguage,
};

export const Settings: React.FC = () => {
  const { show, ToastContainer } = useToast();
  const [settings, setSettings] = useState<SettingsType | null>(null);
  const [formData, setFormData] = useState(initialFormData);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await api.getSettings();
        if (response.success && response.data) {
          setSettings(response.data);
          setFormData((prev) => ({
            ...prev,
            image_resolution: response.data?.image_resolution || '2K',
            image_aspect_ratio: response.data?.image_aspect_ratio || '16:9',
            output_language: response.data?.output_language || 'zh',
          }));
        } else {
          show({ message: response.message || '设置加载失败', type: 'error' });
        }
      } catch (error) {
        show({ message: error instanceof Error ? error.message : '设置加载失败', type: 'error' });
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, [show]);

  const handleSave = async () => {
    if (!formData.api_key.trim() && !settings?.api_key_length) {
      show({ message: '请先填写 API Key', type: 'error' });
      return;
    }

    setIsSaving(true);
    try {
      const payload: Parameters<typeof api.updateSettings>[0] = {
        ...FIXED_SETTINGS,
        image_resolution: formData.image_resolution,
        image_aspect_ratio: formData.image_aspect_ratio,
        output_language: formData.output_language,
        text_api_base_url: '',
        image_api_base_url: '',
        image_caption_api_base_url: '',
        lazyllm_api_keys: {},
      };

      if (formData.api_key.trim()) {
        payload.api_key = formData.api_key.trim();
      }

      const response = await api.updateSettings(payload);
      if (response.success && response.data) {
        setSettings(response.data);
        setFormData((prev) => ({ ...prev, api_key: '' }));
        show({ message: '设置已保存', type: 'success' });
      } else {
        show({ message: response.message || '保存设置失败', type: 'error' });
      }
    } catch (error) {
      show({ message: error instanceof Error ? error.message : '保存设置失败', type: 'error' });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <Loading text="正在加载设置..." />;
  }

  return (
    <>
      <ToastContainer />
      <div className="space-y-8">
        <section className="space-y-4">
          <h2 className="flex items-center text-xl font-semibold text-gray-900 dark:text-foreground-primary">
            <Key size={20} />
            <span className="ml-2">API Key</span>
          </h2>
          <Input
            label="API Key"
            type="password"
            placeholder={settings?.api_key_length ? `已设置，长度 ${settings.api_key_length}` : '请输入你的 API Key'}
            value={formData.api_key}
            onChange={(event) => setFormData((prev) => ({ ...prev, api_key: event.target.value }))}
          />
        </section>

        <section className="space-y-4">
          <h2 className="flex items-center text-xl font-semibold text-gray-900 dark:text-foreground-primary">
            <Image size={20} />
            <span className="ml-2">图像生成配置</span>
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-gray-700 dark:text-foreground-secondary">图像清晰度</span>
              <select
                value={formData.image_resolution}
                onChange={(event) => setFormData((prev) => ({ ...prev, image_resolution: event.target.value }))}
                className="h-10 w-full rounded-lg border border-gray-200 bg-white px-4 text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-banana-500 dark:border-border-primary dark:bg-background-secondary dark:text-foreground-primary"
              >
                <option value="1K">1K</option>
                <option value="2K">2K</option>
                <option value="4K">4K</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-gray-700 dark:text-foreground-secondary">图像比例</span>
              <select
                value={formData.image_aspect_ratio}
                onChange={(event) => setFormData((prev) => ({ ...prev, image_aspect_ratio: event.target.value }))}
                className="h-10 w-full rounded-lg border border-gray-200 bg-white px-4 text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-banana-500 dark:border-border-primary dark:bg-background-secondary dark:text-foreground-primary"
              >
                <option value="16:9">16:9</option>
                <option value="4:3">4:3</option>
                <option value="1:1">1:1</option>
                <option value="3:4">3:4</option>
                <option value="9:16">9:16</option>
              </select>
            </label>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="flex items-center text-xl font-semibold text-gray-900 dark:text-foreground-primary">
            <Languages size={20} />
            <span className="ml-2">输出语言设置</span>
          </h2>
          <select
            value={formData.output_language}
            onChange={(event) => setFormData((prev) => ({ ...prev, output_language: event.target.value as OutputLanguage }))}
            className="h-10 w-full rounded-lg border border-gray-200 bg-white px-4 text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-banana-500 dark:border-border-primary dark:bg-background-secondary dark:text-foreground-primary"
          >
            {Object.entries(languageLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </section>

        <div className="flex justify-end border-t border-gray-200 pt-4 dark:border-border-primary">
          <Button icon={<Save size={18} />} onClick={handleSave} loading={isSaving}>
            {isSaving ? '保存中...' : '保存设置'}
          </Button>
        </div>
      </div>
    </>
  );
};

const SCROLL_SHOW_THRESHOLD = 300;

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [showTop, setShowTop] = useState(false);
  const hasInAppBackHistory = typeof window !== 'undefined' && typeof window.history.state?.idx === 'number'
    ? window.history.state.idx > 0
    : false;
  const canNavigateBack = hasInAppBackHistory || Boolean((location.state as { from?: string } | null)?.from);

  useEffect(() => {
    const onScroll = () => setShowTop(window.scrollY > SCROLL_SHOW_THRESHOLD);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-banana-50 to-yellow-50 dark:from-background-primary dark:to-background-primary">
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <Card className="p-6 md:p-8">
          <div className="space-y-8">
            <div className="flex items-center justify-between border-b border-gray-200 pb-6 dark:border-border-primary">
              <div className="flex items-center">
                <Button
                  variant="secondary"
                  icon={<Home size={18} />}
                  onClick={() => (canNavigateBack ? navigate(-1) : navigate('/'))}
                  className="mr-4"
                >
                  返回首页
                </Button>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-foreground-primary">系统设置</h1>
                  <p className="mt-1 text-sm text-gray-500 dark:text-foreground-tertiary">配置应用参数</p>
                </div>
              </div>
            </div>
            <Settings />
          </div>
        </Card>
      </div>

      {showTop && (
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          aria-label="返回顶部"
          className="fixed bottom-6 right-6 z-40 flex h-11 w-11 items-center justify-center rounded-full bg-white text-gray-700 shadow-lg ring-1 ring-gray-200 transition hover:-translate-y-0.5 hover:bg-banana-50 dark:bg-background-secondary dark:text-foreground-primary dark:ring-border-primary"
        >
          <ArrowUp size={20} />
        </button>
      )}
    </div>
  );
};
