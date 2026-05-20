import React from 'react';
import { Modal } from './Modal';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="使用帮助" size="lg">
      <div className="space-y-4 text-sm leading-6 text-gray-600 dark:text-foreground-secondary">
        <p>先在设置页填写你自己的 API Key 并保存，然后即可创建、编辑和导出幻灯片。</p>
        <p>图像生成配置和输出语言也可以在设置页调整，其余服务配置由系统内置配置提供。</p>
      </div>
    </Modal>
  );
};
