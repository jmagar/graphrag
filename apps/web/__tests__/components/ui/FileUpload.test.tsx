import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileUpload, FileUploadTrigger, FileUploadZone } from '@/components/ui/file-upload';

describe('FileUpload Component', () => {
  it('renders children', () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles}>
        <FileUploadTrigger>
          <button>Upload</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    expect(screen.getByText('Upload')).toBeInTheDocument();
  });

  it('accepts single file by default when multiple is false', () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles} multiple={false}>
        <FileUploadTrigger>
          <button>Upload Single</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).not.toHaveAttribute('multiple');
  });

  it('accepts multiple files when multiple is true', () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles} multiple={true}>
        <FileUploadTrigger>
          <button>Upload Multiple</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toHaveAttribute('multiple');
  });

  it('applies accept attribute for file type filtering', () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles} accept="image/*">
        <FileUploadTrigger>
          <button>Upload Images</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toHaveAttribute('accept', 'image/*');
  });

  it('is disabled when disabled prop is true', () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles} disabled={true}>
        <FileUploadTrigger>
          <button>Upload Disabled</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeDisabled();
  });

  it('calls onFilesAdded when file is selected', async () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles}>
        <FileUploadTrigger>
          <button>Upload</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['content'], 'test.txt', { type: 'text/plain' });
    
    fireEvent.change(input, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(handleFiles).toHaveBeenCalledWith([file]);
    });
  });

  it('handles multiple file selection', async () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles} multiple={true}>
        <FileUploadTrigger>
          <button>Upload Multiple</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file1 = new File(['content1'], 'test1.txt', { type: 'text/plain' });
    const file2 = new File(['content2'], 'test2.txt', { type: 'text/plain' });
    
    fireEvent.change(input, { target: { files: [file1, file2] } });
    
    await waitFor(() => {
      expect(handleFiles).toHaveBeenCalledWith([file1, file2]);
    });
  });

  it('limits to one file when multiple is false', async () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles} multiple={false}>
        <FileUploadTrigger>
          <button>Upload Single</button>
        </FileUploadTrigger>
      </FileUpload>
    );
    
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file1 = new File(['content1'], 'test1.txt', { type: 'text/plain' });
    const file2 = new File(['content2'], 'test2.txt', { type: 'text/plain' });
    
    fireEvent.change(input, { target: { files: [file1, file2] } });
    
    await waitFor(() => {
      expect(handleFiles).toHaveBeenCalledWith([file1]); // Only first file
    });
  });

  it('renders FileUploadZone for drag and drop', () => {
    const handleFiles = jest.fn();
    
    render(
      <FileUpload onFilesAdded={handleFiles}>
        <FileUploadZone>
          <div>Drop files here</div>
        </FileUploadZone>
      </FileUpload>
    );
    
    expect(screen.getByText('Drop files here')).toBeInTheDocument();
  });
});
