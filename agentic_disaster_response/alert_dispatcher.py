"""
Alert Dispatcher for MCP tool execution with error handling and fallbacks.
"""

import asyncio
import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from .mcp_integration import (
    MCPTool, MCPToolSelector, MCPDataFormatter, AlertData, ExecutionResult, ExecutionStatus
)
from .models.mcp_tools import MCPToolRegistry, MCPToolConfig, MCPToolType
from .models.alert_priority import PriorityLevel, AlertPriority
from .models.context import StructuredContext
from .core.exceptions import (
    AlertDispatchError, MCPToolError, MCPToolExecutionError, MCPToolTimeoutError
)


@dataclass
class DispatchResult:
    """Result of alert dispatch operation."""
    success: bool
    total_tools_attempted: int
    successful_dispatches: int
    failed_dispatches: int
    execution_results: List[ExecutionResult] = field(default_factory=list)
    fallback_used: bool = False
    total_execution_time_ms: int = 0
    error_summary: Optional[str] = None


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    max_delay_seconds: float = 30.0


class AlertDispatcher:
    """Dispatches alerts through MCP tools with error handling and fallbacks."""

    def __init__(self, registry: MCPToolRegistry, retry_config: Optional[RetryConfig] = None):
        self.registry = registry
        self.tool_selector = MCPToolSelector(registry)
        self.data_formatter = MCPDataFormatter()
        self.retry_config = retry_config or RetryConfig()
        self.logger = logging.getLogger(f"{__name__}.AlertDispatcher")

        # Track tool performance for intelligent fallback selection
        self.tool_performance: Dict[str, Dict[str, Any]] = {}

    async def dispatch_alerts(self, priority: AlertPriority, context: StructuredContext,
                              message: str, recipients: Optional[List[str]] = None,
                              channels: Optional[List[str]] = None) -> DispatchResult:
        """
        Dispatch alerts through appropriate MCP tools based on priority level.

        Args:
            priority: Alert priority information
            context: Structured context data
            message: Alert message to dispatch
            recipients: Optional list of recipients
            channels: Optional list of channels to use

        Returns:
            DispatchResult with execution details and results
        """
        start_time = time.time()

        # Create alert data structure
        alert_data = AlertData(
            alert_id=f"alert_{context.disaster_info.disaster_id}_{int(start_time)}",
            priority=priority,
            context=context,
            message=message,
            recipients=recipients or [],
            channels=channels or [],
            metadata={"dispatch_timestamp": start_time}
        )

        self.logger.info(
            f"Starting alert dispatch for priority {priority.level.value}")

        # Select appropriate tools for this priority level
        selected_tools = self.tool_selector.select_tools_for_priority(
            priority.level)

        if not selected_tools:
            error_msg = f"No MCP tools available for priority {priority.level.value}"
            self.logger.error(error_msg)
            return DispatchResult(
                success=False,
                total_tools_attempted=0,
                successful_dispatches=0,
                failed_dispatches=0,
                error_summary=error_msg,
                total_execution_time_ms=int((time.time() - start_time) * 1000)
            )

        # Execute tools with fallback logic
        dispatch_result = await self._execute_tools_with_fallback(
            alert_data, selected_tools, priority.level
        )

        dispatch_result.total_execution_time_ms = int(
            (time.time() - start_time) * 1000)

        # Log dispatch completion
        if dispatch_result.success:
            self.logger.info(
                f"Alert dispatch completed successfully: {dispatch_result.successful_dispatches}/"
                f"{dispatch_result.total_tools_attempted} tools succeeded"
            )
        else:
            self.logger.error(
                f"Alert dispatch failed: {dispatch_result.error_summary}"
            )

        return dispatch_result

    async def _execute_tools_with_fallback(self, alert_data: AlertData,
                                           selected_tools: List[MCPToolConfig],
                                           priority: PriorityLevel) -> DispatchResult:
        """Execute tools with fallback logic for failures."""
        execution_results = []
        successful_dispatches = 0
        failed_dispatches = 0
        fallback_used = False

        # Group tools by type for parallel execution within types
        tools_by_type = {}
        for tool in selected_tools:
            if tool.tool_type not in tools_by_type:
                tools_by_type[tool.tool_type] = []
            tools_by_type[tool.tool_type].append(tool)

        # Execute tools by type (alert tools first, then others)
        execution_order = [MCPToolType.ALERT,
                           MCPToolType.ROUTING, MCPToolType.CONTEXT]

        for tool_type in execution_order:
            if tool_type not in tools_by_type:
                continue

            type_tools = tools_by_type[tool_type]
            self.logger.info(
                f"Executing {len(type_tools)} {tool_type.value} tools")

            # Execute tools of this type in parallel
            type_results = await self._execute_tool_type_parallel(
                alert_data, type_tools, priority
            )

            execution_results.extend(type_results)

            # Check if any tools of this type succeeded
            type_successes = sum(
                1 for result in type_results if result.status == ExecutionStatus.SUCCESS)
            type_failures = len(type_results) - type_successes

            successful_dispatches += type_successes
            failed_dispatches += type_failures

            # If all tools of this type failed, try fallbacks
            if type_successes == 0 and type_tools:
                self.logger.warning(
                    f"All {tool_type.value} tools failed, attempting fallbacks")
                fallback_results = await self._execute_fallback_tools(
                    alert_data, type_tools, priority
                )

                if fallback_results:
                    execution_results.extend(fallback_results)
                    fallback_successes = sum(1 for result in fallback_results
                                             if result.status == ExecutionStatus.SUCCESS)
                    successful_dispatches += fallback_successes
                    failed_dispatches += len(fallback_results) - \
                        fallback_successes
                    fallback_used = True

        # Update tool performance tracking
        self._update_tool_performance(execution_results)

        # Determine overall success
        success = successful_dispatches > 0
        error_summary = None if success else "All tool executions failed"

        return DispatchResult(
            success=success,
            total_tools_attempted=len(execution_results),
            successful_dispatches=successful_dispatches,
            failed_dispatches=failed_dispatches,
            execution_results=execution_results,
            fallback_used=fallback_used,
            error_summary=error_summary
        )

    async def _execute_tool_type_parallel(self, alert_data: AlertData,
                                          tools: List[MCPToolConfig],
                                          priority: PriorityLevel) -> List[ExecutionResult]:
        """Execute multiple tools of the same type in parallel."""
        tasks = []

        for tool_config in tools:
            task = self._execute_single_tool_with_retry(
                alert_data, tool_config, priority)
            tasks.append(task)

        # Execute all tools in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed execution results
        execution_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                execution_results.append(ExecutionResult(
                    status=ExecutionStatus.FAILURE,
                    tool_name=tools[i].tool_name,
                    execution_time_ms=0,
                    error_message=str(result)
                ))
            else:
                execution_results.append(result)

        return execution_results

    async def _execute_single_tool_with_retry(self, alert_data: AlertData,
                                              tool_config: MCPToolConfig,
                                              priority: PriorityLevel) -> ExecutionResult:
        """Execute a single tool with retry logic."""
        tool_configuration = tool_config.get_config_for_priority(priority)
        if not tool_configuration:
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=tool_config.tool_name,
                execution_time_ms=0,
                error_message=f"No configuration for priority {priority.value}"
            )

        max_retries = min(self.retry_config.max_retries,
                          tool_configuration.max_retries)

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()

                # Format data for this tool
                formatted_data = self.data_formatter.format_for_tool(
                    alert_data, tool_config, priority
                )

                # Create mock tool instance for execution
                # In a real implementation, this would instantiate the actual MCP tool
                result = await self._mock_tool_execution(
                    tool_config, tool_configuration, formatted_data
                )

                execution_time = int((time.time() - start_time) * 1000)
                result.execution_time_ms = execution_time
                result.retry_count = attempt

                if result.status == ExecutionStatus.SUCCESS:
                    self.logger.info(
                        f"Tool {tool_config.tool_name} executed successfully on attempt {attempt + 1}"
                    )
                    return result

                # If not success and we have more retries, wait before retrying
                if attempt < max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(
                        f"Tool {tool_config.tool_name} failed on attempt {attempt + 1}, "
                        f"retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

            except asyncio.TimeoutError:
                self.logger.error(
                    f"Tool {tool_config.tool_name} timed out on attempt {attempt + 1}")
                if attempt == max_retries:
                    return ExecutionResult(
                        status=ExecutionStatus.TIMEOUT,
                        tool_name=tool_config.tool_name,
                        execution_time_ms=tool_configuration.timeout_seconds * 1000,
                        error_message="Tool execution timed out",
                        retry_count=attempt
                    )

            except Exception as e:
                self.logger.error(
                    f"Tool {tool_config.tool_name} failed on attempt {attempt + 1}: {str(e)}"
                )
                if attempt == max_retries:
                    return ExecutionResult(
                        status=ExecutionStatus.FAILURE,
                        tool_name=tool_config.tool_name,
                        execution_time_ms=int(
                            (time.time() - start_time) * 1000),
                        error_message=str(e),
                        retry_count=attempt
                    )

        # Should not reach here, but return failure as fallback
        return ExecutionResult(
            status=ExecutionStatus.FAILURE,
            tool_name=tool_config.tool_name,
            execution_time_ms=0,
            error_message="Maximum retries exceeded",
            retry_count=max_retries
        )

    async def _execute_fallback_tools(self, alert_data: AlertData,
                                      failed_tools: List[MCPToolConfig],
                                      priority: PriorityLevel) -> List[ExecutionResult]:
        """Execute fallback tools for failed primary tools."""
        fallback_results = []

        for failed_tool in failed_tools:
            fallback_tool_configs = self.tool_selector.get_fallback_tools(
                failed_tool, priority)

            for fallback_config in fallback_tool_configs:
                self.logger.info(
                    f"Attempting fallback tool {fallback_config.tool_name} "
                    f"for failed tool {failed_tool.tool_name}"
                )

                result = await self._execute_single_tool_with_retry(
                    alert_data, fallback_config, priority
                )
                fallback_results.append(result)

                # If fallback succeeds, don't try more fallbacks for this tool
                if result.status == ExecutionStatus.SUCCESS:
                    break

        return fallback_results

    async def _mock_tool_execution(self, tool_config: MCPToolConfig,
                                   tool_configuration, formatted_data: Dict[str, Any]) -> ExecutionResult:
        """
        Mock tool execution for testing purposes.
        In a real implementation, this would call the actual MCP tool.
        """
        # Simulate network delay
        await asyncio.sleep(0.1)

        # Simulate success/failure based on tool name (for testing)
        if "backup" in tool_config.tool_name.lower():
            # Backup tools have lower success rate
            import random
            success = random.random() > 0.3
        else:
            # Primary tools have higher success rate
            import random
            success = random.random() > 0.1

        if success:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                tool_name=tool_config.tool_name,
                execution_time_ms=0,  # Will be set by caller
                response_data={
                    "message": "Alert dispatched successfully",
                    "recipients_notified": len(formatted_data.get("recipients", [])),
                    "channels_used": len(formatted_data.get("channels", []))
                }
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=tool_config.tool_name,
                execution_time_ms=0,  # Will be set by caller
                error_message="Simulated tool failure"
            )

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay before retry using exponential backoff."""
        if not self.retry_config.exponential_backoff:
            return self.retry_config.base_delay_seconds

        delay = self.retry_config.base_delay_seconds * (2 ** attempt)
        return min(delay, self.retry_config.max_delay_seconds)

    def _update_tool_performance(self, execution_results: List[ExecutionResult]) -> None:
        """Update tool performance tracking for future optimization."""
        for result in execution_results:
            tool_name = result.tool_name

            if tool_name not in self.tool_performance:
                self.tool_performance[tool_name] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "average_execution_time_ms": 0,
                    "failure_rate": 0.0
                }

            stats = self.tool_performance[tool_name]
            stats["total_executions"] += 1

            if result.status == ExecutionStatus.SUCCESS:
                stats["successful_executions"] += 1

            # Update average execution time
            current_avg = stats["average_execution_time_ms"]
            total_executions = stats["total_executions"]
            stats["average_execution_time_ms"] = (
                (current_avg * (total_executions - 1) +
                 result.execution_time_ms) / total_executions
            )

            # Update failure rate
            stats["failure_rate"] = 1.0 - \
                (stats["successful_executions"] / stats["total_executions"])

    def get_tool_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for all tools."""
        return self.tool_performance.copy()

    def reset_tool_performance_stats(self) -> None:
        """Reset tool performance statistics."""
        self.tool_performance.clear()
        self.logger.info("Tool performance statistics reset")
