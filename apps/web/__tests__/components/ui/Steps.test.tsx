import { render, screen, fireEvent } from '@testing-library/react';
import { Steps, StepsItem, StepsTrigger, StepsContent } from '@/components/ui/steps';

describe('Steps Component', () => {
  it('renders steps container', () => {
    render(
      <Steps>
        <div>Step content</div>
      </Steps>
    );
    
    expect(screen.getByText('Step content')).toBeInTheDocument();
  });

  it('renders individual step items', () => {
    render(
      <Steps>
        <StepsItem value="step1">
          <StepsTrigger>Step 1</StepsTrigger>
          <StepsContent>Step 1 content</StepsContent>
        </StepsItem>
        <StepsItem value="step2">
          <StepsTrigger>Step 2</StepsTrigger>
          <StepsContent>Step 2 content</StepsContent>
        </StepsItem>
      </Steps>
    );
    
    expect(screen.getByText('Step 1')).toBeInTheDocument();
    expect(screen.getByText('Step 2')).toBeInTheDocument();
  });

  it('shows step content when trigger is clicked', () => {
    render(
      <Steps>
        <StepsItem value="step1">
          <StepsTrigger>Click me</StepsTrigger>
          <StepsContent>Hidden content</StepsContent>
        </StepsItem>
      </Steps>
    );
    
    const trigger = screen.getByText('Click me');
    fireEvent.click(trigger);
    
    // Content should be visible after click
    expect(screen.getByText('Hidden content')).toBeVisible();
  });

  it('supports multiple steps', () => {
    render(
      <Steps>
        <StepsItem value="step1">
          <StepsTrigger>Step 1</StepsTrigger>
          <StepsContent>Content 1</StepsContent>
        </StepsItem>
        <StepsItem value="step2">
          <StepsTrigger>Step 2</StepsTrigger>
          <StepsContent>Content 2</StepsContent>
        </StepsItem>
        <StepsItem value="step3">
          <StepsTrigger>Step 3</StepsTrigger>
          <StepsContent>Content 3</StepsContent>
        </StepsItem>
      </Steps>
    );
    
    expect(screen.getByText('Step 1')).toBeInTheDocument();
    expect(screen.getByText('Step 2')).toBeInTheDocument();
    expect(screen.getByText('Step 3')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <Steps className="custom-steps">
        <div>Content</div>
      </Steps>
    );
    
    expect(container.firstChild).toHaveClass('custom-steps');
  });

  it('renders nested content in steps', () => {
    render(
      <Steps>
        <StepsItem value="step1">
          <StepsTrigger>Trigger</StepsTrigger>
          <StepsContent>
            <div>
              <strong>Bold</strong>
              <p>Paragraph</p>
            </div>
          </StepsContent>
        </StepsItem>
      </Steps>
    );
    
    fireEvent.click(screen.getByText('Trigger'));
    
    expect(screen.getByText('Bold')).toBeInTheDocument();
    expect(screen.getByText('Paragraph')).toBeInTheDocument();
  });
});
