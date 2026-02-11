# Generated migration for normalizing approval chains

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0030_department_shortname'),
    ]

    operations = [
        # 1. Создаем новые модели для цепочек
        migrations.CreateModel(
            name='TaskApprovalChain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('pending', 'Ожидание'), ('approved', 'Одобрено'), ('rejected', 'Отклонено')], default='pending', max_length=20)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('approver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tasks.employee')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_chain', to='tasks.task')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='TaskReviewChain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('pending', 'Ожидание'), ('approved', 'Одобрено'), ('rejected', 'Отклонено')], default='pending', max_length=20)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('review_comment', models.TextField(blank=True, null=True)),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tasks.employee')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_chain', to='tasks.task')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='TaskRedirectChain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField()),
                ('redirected_at', models.DateTimeField(auto_now_add=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('from_employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='redirected_from', to='tasks.employee')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='redirect_chain', to='tasks.task')),
                ('to_employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='redirected_to', to='tasks.employee')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        
        # 2. Добавляем индексы для производительности
        migrations.AddIndex(
            model_name='taskapprovalchain',
            index=models.Index(fields=['task', 'status'], name='tasks_task__task_s_idx'),
        ),
        migrations.AddIndex(
            model_name='taskapprovalchain',
            index=models.Index(fields=['approver', 'status'], name='tasks_task__appro_idx'),
        ),
        migrations.AddIndex(
            model_name='taskreviewchain',
            index=models.Index(fields=['task', 'status'], name='tasks_task__task_s_rev_idx'),
        ),
        migrations.AddIndex(
            model_name='taskreviewchain',
            index=models.Index(fields=['reviewer', 'status'], name='tasks_task__rev_s_idx'),
        ),
        migrations.AddIndex(
            model_name='taskredirectchain',
            index=models.Index(fields=['from_employee', 'to_employee'], name='tasks_task__from_to_idx'),
        ),
        
        # 3. Добавляем unique constraints
        migrations.AlterUniqueTogether(
            name='taskapprovalchain',
            unique_together={('task', 'order')},
        ),
        migrations.AlterUniqueTogether(
            name='taskreviewchain',
            unique_together={('task', 'order')},
        ),
        migrations.AlterUniqueTogether(
            name='taskredirectchain',
            unique_together={('task', 'order')},
        ),
    ]
