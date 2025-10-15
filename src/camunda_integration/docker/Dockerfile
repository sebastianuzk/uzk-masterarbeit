# Custom Camunda Platform 7 without demo processes
FROM camunda/camunda-bpm-platform:7.21.0

# Switch to root to modify files
USER root

# Remove demo applications and processes
RUN rm -rf /camunda/webapps/camunda-invoice* \
    && rm -rf /camunda/webapps/h2-console \
    && find /camunda -name "*invoice*" -type f -delete \
    && find /camunda -name "*Invoice*" -type f -delete

# Remove demo process definitions from auto-deployment
RUN find /camunda -path "*/WEB-INF/classes/META-INF/processes.xml" -delete || true \
    && find /camunda -path "*/processes" -type d -exec rm -rf {} + || true \
    && find /camunda -name "*.bpmn" -not -path "*/camunda-engine/*" -delete || true

# Clean up any remaining demo files
RUN find /camunda -type f -name "*demo*" -delete || true \
    && find /camunda -type f -name "*sample*" -delete || true

# Switch back to camunda user
USER camunda

# Environment variables for clean startup
ENV DB_DRIVER=org.h2.Driver
ENV DB_URL=jdbc:h2:mem:camunda;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
ENV DB_USERNAME=sa
ENV DB_PASSWORD=sa
ENV JAVA_OPTS=-Xmx512m -XX:MaxMetaspaceSize=256m

# Use default Camunda startup (no auto-deployment)
CMD ["/camunda/camunda.sh"]